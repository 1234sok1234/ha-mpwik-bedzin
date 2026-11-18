"""Scheduler (DataUpdateCoordinator) dla integracji MPWiK Będzin."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MpwikApiError, MpwikAuthError, MpwikClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MpwikCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Zarządza cyklicznym pobieraniem danych zgodnie z wybranym interwałem."""

    def __init__(self, hass: HomeAssistant, client: MpwikClient, interval_hours: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=interval_hours),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Wywoływane automatycznie przez scheduler Home Assistanta."""
        try:
            return await self.client.async_get_accountancy()
        except MpwikAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MpwikApiError as err:
            raise UpdateFailed(f"Błąd komunikacji z iBOK: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Nieoczekiwany błąd: {err}") from err
