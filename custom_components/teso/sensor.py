"""Sensoren voor de TESO integratie."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import TesoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Stel TESO sensoren in."""
    coordinator: TesoCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for pass_data in coordinator.data:
        card_number = pass_data.get("card_number", "onbekend")

        # Apparaat info (gedeeld door alle sensoren van deze pas)
        device_info = DeviceInfo(
            identifiers={(DOMAIN, card_number)},
            name=f"TESO-pas {card_number}",
            manufacturer="TESO",
            model="TESO-pas",
            configuration_url="https://www.teso.nl/my-teso/my-passes/",
        )

        # Sensor: resterende overtochten (per product)
        for product in pass_data.get("products", []):
            entities.append(
                TesoRemainingTrips(coordinator, pass_data, product, device_info)
            )

        # Sensor: gekoppeld kenteken
        if pass_data.get("license_plate"):
            entities.append(TesoLicensePlate(coordinator, pass_data, device_info))

        # Sensor: laatste overtocht
        entities.append(TesoLastTrip(coordinator, pass_data, device_info))

    async_add_entities(entities)


class TesoBaseSensor(CoordinatorEntity, SensorEntity):
    """Basis sensor klasse voor TESO."""

    def __init__(
        self,
        coordinator: TesoCoordinator,
        pass_data: dict,
        device_info: DeviceInfo,
    ) -> None:
        """Initialiseer de basis sensor."""
        super().__init__(coordinator)
        self._card_number = pass_data.get("card_number", "onbekend")
        self._attr_device_info = device_info

    def _get_pass_data(self) -> dict | None:
        """Haal de actuele pasgegevens op uit de coordinator."""
        for pass_data in self.coordinator.data:
            if pass_data.get("card_number") == self._card_number:
                return pass_data
        return None


class TesoRemainingTrips(TesoBaseSensor):
    """Sensor voor het aantal resterende overtochten per product."""

    def __init__(
        self,
        coordinator: TesoCoordinator,
        pass_data: dict,
        product: dict,
        device_info: DeviceInfo,
    ) -> None:
        """Initialiseer de sensor."""
        super().__init__(coordinator, pass_data, device_info)
        self._product_name = product["name"]

        self._attr_unique_id = (
            f"teso_{self._card_number}_remaining_{self._product_name}"
            .replace(" ", "_").lower()
        )
        self._attr_name = f"Resterende overtochten - {self._product_name}"
        self._attr_icon = "mdi:ferry"
        self._attr_native_unit_of_measurement = "overtochten"

    @property
    def native_value(self) -> int | None:
        """Geef het aantal resterende overtochten terug."""
        pass_data = self._get_pass_data()
        if not pass_data:
            return None
        for product in pass_data.get("products", []):
            if product["name"] == self._product_name:
                return product["remaining"]
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Geef extra attributen terug."""
        return {
            "pasnummer": self._card_number,
            "product": self._product_name,
        }


class TesoLicensePlate(TesoBaseSensor):
    """Sensor voor het gekoppelde kenteken."""

    def __init__(
        self,
        coordinator: TesoCoordinator,
        pass_data: dict,
        device_info: DeviceInfo,
    ) -> None:
        """Initialiseer de sensor."""
        super().__init__(coordinator, pass_data, device_info)

        self._attr_unique_id = f"teso_{self._card_number}_license_plate"
        self._attr_name = "Gekoppeld kenteken"
        self._attr_icon = "mdi:car"

    @property
    def native_value(self) -> str | None:
        """Geef het gekoppelde kenteken terug."""
        pass_data = self._get_pass_data()
        if not pass_data:
            return None
        return pass_data.get("license_plate")

    @property
    def extra_state_attributes(self) -> dict:
        """Geef extra attributen terug."""
        pass_data = self._get_pass_data()
        attrs = {"pasnummer": self._card_number}
        if pass_data:
            vehicle = pass_data.get("vehicle")
            if vehicle:
                attrs["voertuig"] = vehicle
        return attrs


class TesoLastTrip(TesoBaseSensor):
    """Sensor voor de laatste overtocht."""

    def __init__(
        self,
        coordinator: TesoCoordinator,
        pass_data: dict,
        device_info: DeviceInfo,
    ) -> None:
        """Initialiseer de sensor."""
        super().__init__(coordinator, pass_data, device_info)

        self._attr_unique_id = f"teso_{self._card_number}_last_trip"
        self._attr_name = "Laatste overtocht"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Geef de datum/tijd van de laatste overtocht terug."""
        pass_data = self._get_pass_data()
        if not pass_data:
            return None
        last_trip = pass_data.get("last_trip")
        if isinstance(last_trip, datetime):
            # Home Assistant verwacht timezone-aware datetimes
            from homeassistant.util import dt as dt_util
            return dt_util.as_local(last_trip)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Geef extra attributen terug."""
        return {"pasnummer": self._card_number}
