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


def _parse_pln(value: str | float | int | None) -> float:
    """Konwertuje polski zapis kwoty (np. '1 413,80') na float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


class MpwikClient:
    """Lekki klient HTTP korzystający z sesji aiohttp Home Assistanta."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def async_get_accountancy(self) -> dict[str, Any]:
        """Loguje się do iBOK i pobiera dane z modułu Accountancy_v3."""
        async with self._session.get(
            BASE_URL,
            headers=DEFAULT_HEADERS,
            timeout=aiohttp.ClientTimeout(total=20),
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
            BASE_URL,
            data=payload,
            headers=DEFAULT_HEADERS,
            timeout=aiohttp.ClientTimeout(total=20),
            allow_redirects=True,
        ) as resp:
            if resp.status not in (200, 302):
                raise MpwikApiError(f"Błąd podczas logowania: HTTP {resp.status}")

        ts = int(time.time() * 1000)
        url = f"{BASE_URL}?module=Accountancy_v3&_t={ts}"
        xhr_headers = {**DEFAULT_HEADERS, "X-Requested-With": "XMLHttpRequest"}

        async with self._session.get(
            url,
            headers=xhr_headers,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                raise MpwikApiError(f"Błąd pobierania rozrachunków: HTTP {resp.status}")

            try:
                raw = await resp.json(content_type=None)
            except Exception as err:
                raise MpwikAuthError("Nie udało się zalogować (sprawdź login i hasło)") from err

        if not isinstance(raw, dict) or "pozycje" not in raw:
            raise MpwikAuthError("Brak danych rozrachunków — nieprawidłowe logowanie")

        return self._normalize_data(raw)

    def _normalize_data(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Przetwarza surowy JSON na czytelne dane dla sensorów HA."""
        total_due = _parse_pln(raw.get("roznica"))
        total_charged = _parse_pln(raw.get("sumawn"))
        total_paid = _parse_pln(raw.get("sumama"))

        unpaid_invoices: list[dict[str, Any]] = []
        for item in raw.get("pozycje", []):
            if "ro" in item:
                item_due = _parse_pln(item.get("ro"))
            else:
                item_due = round(_parse_pln(item.get("wn")) - _parse_pln(item.get("ma")), 2)

            if item_due > 0:
                unpaid_invoices.append({
                    "number": item.get("nr"),
                    "issued": item.get("dw"),
                    "due_date": item.get("tp"),
                    "amount_total": _parse_pln(item.get("wn")),
                    "amount_due": item_due,
                })

        unpaid_invoices.sort(key=lambda x: x.get("due_date") or "9999-99-99")
        next_due_date = unpaid_invoices[0]["due_date"] if unpaid_invoices else None

        return {
            "total_due": total_due,
            "total_charged": total_charged,
            "total_paid": total_paid,
            "unpaid_count": len(unpaid_invoices),
            "next_due_date": next_due_date,
            "unpaid_invoices": unpaid_invoices,
        }
