"""Konfiguracja w UI (Config Flow + zmiana interwału w Options Flow)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import MpwikApiError, MpwikAuthError, MpwikClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    MAX_SCAN_INTERVAL_HOURS,
    MIN_SCAN_INTERVAL_HOURS,
)


class MpwikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Kreator dodawania konta MPWiK Będzin w UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_create_clientsession(self.hass)
            client = MpwikClient(
                session,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_get_accountancy()
            except MpwikAuthError:
                errors["base"] = "invalid_auth"
            except MpwikApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"mpwik_{user_input[CONF_USERNAME]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"MPWiK Będzin ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_HOURS): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL_HOURS, max=MAX_SCAN_INTERVAL_HOURS),
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Rejestruje okno opcji (przycisk Configure przy integracji)."""
        return MpwikOptionsFlow()


class MpwikOptionsFlow(config_entries.OptionsFlow):
    """Pozwala zmienić interwał odświeżania bez usuwania integracji."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS),
        )

        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL_HOURS, max=MAX_SCAN_INTERVAL_HOURS),
            ),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
