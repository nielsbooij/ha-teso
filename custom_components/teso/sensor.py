"""Sensoren voor de TESO integratie."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
        for product in pass_data.get("products", []):
            entities.append(TesoPassSensor(coordinator, pass_data, product))

    async_add_entities(entities)


class TesoPassSensor(CoordinatorEntity, SensorEntity):
    """Sensor die het aantal resterende overtochten bijhoudt."""

    def __init__(
        self,
        coordinator: TesoCoordinator,
        pass_data: dict,
        product: dict,
    ) -> None:
        """Initialiseer de sensor."""
        super().__init__(coordinator)
        self._pass_data = pass_data
        self._product_name = product["name"]
        self._card_number = pass_data.get("card_number", "onbekend")
        self._license_plate = pass_data.get("license_plate", "")

        # Unieke ID op basis van pasnummer + productnaam
        self._attr_unique_id = (
            f"teso_{self._card_number}_{self._product_name}".replace(" ", "_").lower()
        )

        # Naam van de sensor
        if self._license_plate:
            self._attr_name = f"TESO {self._license_plate} - {self._product_name}"
        else:
            self._attr_name = f"TESO {self._card_number} - {self._product_name}"

        self._attr_icon = "mdi:ferry"
        self._attr_native_unit_of_measurement = "overtochten"

    @property
    def native_value(self) -> int | None:
        """Geef het aantal resterende overtochten terug."""
        for pass_data in self.coordinator.data:
            if pass_data.get("card_number") == self._card_number:
                for product in pass_data.get("products", []):
                    if product["name"] == self._product_name:
                        return product["remaining"]
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Geef extra attributen terug."""
        attrs = {
            "pasnummer": self._card_number,
            "product": self._product_name,
        }
        if self._license_plate:
            attrs["kenteken"] = self._license_plate

        vehicle = self._pass_data.get("vehicle")
        if vehicle:
            attrs["voertuig"] = vehicle

        return attrs
