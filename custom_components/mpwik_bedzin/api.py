"""Klient API do portalu iBOK MPWiK Będzin."""
from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/157.0.0.0 Safari/537.36"
    ),
    "Origin": "https://ibok.mpwik.bedzin.pl",
    "Referer": "https://ibok.mpwik.bedzin.pl/",
}


class MpwikAuthError(Exception):
    """Błąd nieprawidłowych danych logowania."""


class MpwikApiError(Exception):
    """Ogólny błąd komunikacji z iBOK."""


def _parse_num(value: str | float | int | None) -> float:
    """Konwertuje polski zapis liczby (np. '1 413,80') na float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return round(float(cleaned), 3)
    except ValueError:
        return 0.0


class MpwikClient:
    """Lekki klient HTTP korzystający z sesji aiohttp Home Assistanta."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def async_get_accountancy(self) -> dict[str, Any]:
        """Loguje się do iBOK, pobiera rozrachunki oraz odczyty i wylogowuje sesję."""
        try:
            async with self._session.get(
                BASE_URL, headers=DEFAULT_HEADERS, timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                if resp.status != 200:
                    raise MpwikApiError(f"Błąd otwarcia strony logowania: HTTP {resp.status}")

            payload = {
                "JSTest": "ok",
                "user": self._username,
                "pass": self._password,
                "login": "Zaloguj",
            }
            async with self._session.post(
                BASE_URL, data=payload, headers=DEFAULT_HEADERS,
                timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True,
            ) as resp:
                if resp.status not in (200, 302):
                    raise MpwikApiError(f"Błąd podczas logowania: HTTP {resp.status}")

            ts = int(time.time() * 1000)
            xhr_headers = {**DEFAULT_HEADERS, "X-Requested-With": "XMLHttpRequest"}

            async with self._session.get(
                f"{BASE_URL}?module=Accountancy_v3&_t={ts}",
                headers=xhr_headers, timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    raise MpwikApiError(f"Błąd pobierania rozrachunków: HTTP {resp.status}")
                try:
                    raw_acc = await resp.json(content_type=None)
                except Exception as err:
                    raise MpwikAuthError("Nie udało się zalogować (sprawdź login, hasło lub CAPTCHA)") from err

            if not isinstance(raw_acc, dict) or "pozycje" not in raw_acc:
                raise MpwikAuthError("Brak danych rozrachunków — nieprawidłowe logowanie")

            raw_readouts: Any = None
            try:
                async with self._session.get(
                    f"{BASE_URL}?module=Readouts_v1&_t={ts}",
                    headers=xhr_headers, timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 200:
                        raw_readouts = await resp.json(content_type=None)
            except Exception as err:
                _LOGGER.warning("Nie udało się pobrać odczytów wodomierza: %s", err)

            return self._normalize_data(raw_acc, raw_readouts)
        finally:
            try:
                async with self._session.get(
                    f"{BASE_URL}?logout=true&kill=true",
                    headers=DEFAULT_HEADERS, timeout=aiohttp.ClientTimeout(total=10),
                ):
                    pass
            except Exception:
                pass

    def _normalize_data(self, raw_acc: dict[str, Any], raw_readouts: Any) -> dict[str, Any]:
        """Przetwarza surowy JSON faktur i odczytów na dane dla sensorów HA."""
        all_invoices: list[dict[str, Any]] = []
        unpaid_invoices: list[dict[str, Any]] = []

        for item in raw_acc.get("pozycje", []):
            amount_total = round(_parse_num(item.get("wn")), 2)
            amount_paid = round(_parse_num(item.get("ma")), 2)
            item_due = round(_parse_num(item.get("ro")), 2) if "ro" in item else round(amount_total - amount_paid, 2)
            inv = {
                "number": item.get("nr"),
                "issued": item.get("dw"),
                "due_date": item.get("tp"),
                "amount_total": amount_total,
                "amount_paid": amount_paid,
                "amount_due": item_due,
            }
            all_invoices.append(inv)
            if item_due > 0:
                unpaid_invoices.append(inv)

        unpaid_invoices.sort(key=lambda x: x.get("due_date") or "9999-99-99")
        readouts = self._extract_readouts(raw_readouts)
        latest = readouts[0] if readouts else {}
        consumption = (
            round(readouts[0]["reading_m3"] - readouts[1]["reading_m3"], 3)
            if len(readouts) >= 2
            else latest.get("consumption_m3", 0.0)
        )

        return {
            "total_due": round(_parse_num(raw_acc.get("roznica")), 2),
            "total_charged": round(_parse_num(raw_acc.get("sumawn")), 2),
            "total_paid": round(_parse_num(raw_acc.get("sumama")), 2),
            "unpaid_count": len(unpaid_invoices),
            "next_due_date": unpaid_invoices[0]["due_date"] if unpaid_invoices else None,
            "unpaid_invoices": unpaid_invoices,
            "invoices": all_invoices,
            "water_meter_m3": latest.get("reading_m3"),
            "water_consumption_m3": consumption,
            "water_meter_info": latest,
            "water_readouts": readouts[:24],
        }

    def _extract_readouts(self, raw_readouts: Any) -> list[dict[str, Any]]:
        """Wyciąga i sortuje odczyty wodomierza z listy liczników."""
        items: list[dict[str, Any]] = []
        serial_default = None

        if isinstance(raw_readouts, list) and raw_readouts:
            first = raw_readouts[0]
            if isinstance(first, dict) and isinstance(first.get("odczyty"), list):
                serial_default = first.get("numer_fabryczny") or first.get("nr_fabryczny")
                items = first["odczyty"]
            else:
                items = raw_readouts
        elif isinstance(raw_readouts, dict):
            serial_default = raw_readouts.get("numer_fabryczny")
            items = raw_readouts.get("odczyty") or raw_readouts.get("pozycje") or []

        parsed: list[dict[str, Any]] = []
        for r in items:
            if not isinstance(r, dict):
                continue
            parsed.append({
                "date": r.get("do") or r.get("data"),
                "reading_m3": _parse_num(r.get("sl")),
                "consumption_m3": _parse_num(r.get("zu")),
                "type": r.get("typ"),
                "serial_number": r.get("numer_fabryczny") or serial_default,
            })
        parsed.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
        return parsed
