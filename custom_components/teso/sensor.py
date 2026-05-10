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

    # Passen
    for pass_data in coordinator.data.get("passes", []):
        card_number = pass_data.get("card_number", "onbekend")

        device_info = DeviceInfo(
            identifiers={(DOMAIN, card_number)},
            name=f"TESO-pas {card_number}",
            manufacturer="TESO",
            model="TESO-pas",
            configuration_url="https://www.teso.nl/my-teso/my-passes/",
        )

        for product in pass_data.get("products", []):
            entities.append(
                TesoRemainingTrips(coordinator, pass_data, product, device_info)
            )

        if pass_data.get("license_plate"):
            entities.append(TesoLicensePlate(coordinator, pass_data, device_info))

        entities.append(TesoLastTrip(coordinator, pass_data, device_info))

    # E-tickets
    for ticket_data in coordinator.data.get("tickets", []):
        ticket_number = ticket_data.get("ticket_number", "onbekend")

        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ticket_{ticket_number}")},
            name=f"TESO e-ticket {ticket_number}",
            manufacturer="TESO",
            model="TESO e-ticket",
            configuration_url="https://www.teso.nl/my-teso/loose-tickets/",
        )

        entities.append(TesoTicketSaldo(coordinator, ticket_data, device_info))

    async_add_entities(entities)


class TesoBaseSensor(CoordinatorEntity, SensorEntity):
    """Basis sensor klasse voor TESO."""

    def __init__(self, coordinator, pass_data, device_info):
        super().__init__(coordinator)
        self._card_number = pass_data.get("card_number", "onbekend")
        self._attr_device_info = device_info

    def _get_pass_data(self):
        for pass_data in self.coordinator.data.get("passes", []):
            if pass_data.get("card_number") == self._card_number:
                return pass_data
        return None


class TesoRemainingTrips(TesoBaseSensor):
    def __init__(self, coordinator, pass_data, product, device_info):
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
    def native_value(self):
        pass_data = self._get_pass_data()
        if not pass_data:
            return None
        for product in pass_data.get("products", []):
            if product["name"] == self._product_name:
                return product["remaining"]
        return None

    @property
    def extra_state_attributes(self):
        return {"pasnummer": self._card_number, "product": self._product_name}


class TesoLicensePlate(TesoBaseSensor):
    def __init__(self, coordinator, pass_data, device_info):
        super().__init__(coordinator, pass_data, device_info)
        self._attr_unique_id = f"teso_{self._card_number}_license_plate"
        self._attr_name = f"Gekoppeld kenteken {self._card_number}"
        self._attr_icon = "mdi:car"

    @property
    def native_value(self):
        pass_data = self._get_pass_data()
        return pass_data.get("license_plate") if pass_data else None

    @property
    def extra_state_attributes(self):
        pass_data = self._get_pass_data()
        attrs = {"pasnummer": self._card_number}
        if pass_data and pass_data.get("vehicle"):
            attrs["voertuig"] = pass_data["vehicle"]
        return attrs


class TesoLastTrip(TesoBaseSensor):
    def __init__(self, coordinator, pass_data, device_info):
        super().__init__(coordinator, pass_data, device_info)
        self._attr_unique_id = f"teso_{self._card_number}_last_trip"
        self._attr_name = f"Laatste overtocht {self._card_number}"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        pass_data = self._get_pass_data()
        if not pass_data:
            return None
        last_trip = pass_data.get("last_trip")
        if isinstance(last_trip, datetime):
            from homeassistant.util import dt as dt_util
            return dt_util.as_local(last_trip)
        return None

    @property
    def extra_state_attributes(self):
        return {"pasnummer": self._card_number}


class TesoTicketSaldo(CoordinatorEntity, SensorEntity):
    """Sensor voor een TESO e-ticket."""

    def __init__(self, coordinator, ticket_data, device_info):
        super().__init__(coordinator)
        self._ticket_number = ticket_data.get("ticket_number", "onbekend")
        self._attr_device_info = device_info
        self._attr_unique_id = f"teso_ticket_{self._ticket_number}_saldo"
        self._attr_name = f"E-ticket saldo {self._ticket_number}"
        self._attr_icon = "mdi:ticket-confirmation"
        self._attr_native_unit_of_measurement = "retours"

    def _get_ticket_data(self):
        for ticket in self.coordinator.data.get("tickets", []):
            if ticket.get("ticket_number") == self._ticket_number:
                return ticket
        return None

    @property
    def native_value(self):
        ticket = self._get_ticket_data()
        return ticket.get("remaining") if ticket else None

    @property
    def extra_state_attributes(self):
        ticket = self._get_ticket_data()
        if not ticket:
            return {}
        return {
            "ticket_nummer": self._ticket_number,
            "product": ticket.get("ticket_name", ""),
            "aankoopdatum": ticket.get("purchase_date", ""),
            "qr_code": ticket.get("qr_code", ""),
        }
