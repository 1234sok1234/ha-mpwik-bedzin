"""Sensory dla integracji MPWiK Będzin iBOK."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MpwikCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Rejestruje encje sensorów."""
    coordinator: MpwikCoordinator = hass.data[DOMAIN][entry.entry_id]
    username = entry.data[CONF_USERNAME]

    async_add_entities([
        MpwikAmountDueSensor(coordinator, entry.entry_id, username),
        MpwikNextDueDateSensor(coordinator, entry.entry_id, username),
        MpwikUnpaidCountSensor(coordinator, entry.entry_id, username),
        MpwikWaterMeterSensor(coordinator, entry.entry_id, username),
    ])


class MpwikBaseSensor(CoordinatorEntity[MpwikCoordinator], SensorEntity):
    """Wspólna klasa bazowa dla sensorów MPWiK."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MpwikCoordinator, entry_id: str, username: str) -> None:
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"MPWiK Będzin ({username})",
            "manufacturer": "MPWiK Będzin",
            "model": "iBOK",
        }

class MpwikAmountDueSensor(MpwikBaseSensor):
    """Łączna kwota do zapłaty (PLN) + pełna historia faktur w atrybutach."""

    _attr_name = "Amount due"
    _attr_native_unit_of_measurement = "PLN"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:water-check"

    def __init__(self, coordinator: MpwikCoordinator, entry_id: str, username: str) -> None:
        super().__init__(coordinator, entry_id, username)
        self._attr_unique_id = f"{entry_id}_amount_due"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("total_due")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total_charged": self.coordinator.data.get("total_charged"),
            "total_paid": self.coordinator.data.get("total_paid"),
            "unpaid_invoices": self.coordinator.data.get("unpaid_invoices", []),
            "invoices": self.coordinator.data.get("invoices", []),
        }


class MpwikNextDueDateSensor(MpwikBaseSensor):
    """Najbliższy termin płatności nieopłaconej faktury."""

    _attr_name = "Next due date"
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, coordinator: MpwikCoordinator, entry_id: str, username: str) -> None:
        super().__init__(coordinator, entry_id, username)
        self._attr_unique_id = f"{entry_id}_next_due_date"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("next_due_date")


class MpwikUnpaidCountSensor(MpwikBaseSensor):
    """Liczba nieopłaconych faktur."""

    _attr_name = "Unpaid invoices"
    _attr_icon = "mdi:file-document-alert-outline"

    def __init__(self, coordinator: MpwikCoordinator, entry_id: str, username: str) -> None:
        super().__init__(coordinator, entry_id, username)
        self._attr_unique_id = f"{entry_id}_unpaid_count"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("unpaid_count")


class MpwikWaterMeterSensor(MpwikBaseSensor):
    """Stan wodomierza (m³) zgodny z Energy Dashboard."""

    _attr_name = "Water meter"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: MpwikCoordinator, entry_id: str, username: str) -> None:
        super().__init__(coordinator, entry_id, username)
        self._attr_unique_id = f"{entry_id}_water_meter"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("water_meter_m3")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = self.coordinator.data.get("water_meter_info") or {}
        return {
            "serial_number": info.get("serial_number"),
            "last_reading_date": info.get("date"),
            "last_consumption_m3": info.get("consumption_m3"),
            "last_reading_type": info.get("type"),
            "history": self.coordinator.data.get("water_readouts", []),
        }
