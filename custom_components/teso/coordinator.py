"""Data coordinator voor de TESO integratie."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.teso.nl"
LOGIN_URL = f"{BASE_URL}/my-teso/login/"
PASSES_URL = f"{BASE_URL}/my-teso/my-passes/"

UPDATE_INTERVAL = timedelta(hours=1)


class TesoCoordinator(DataUpdateCoordinator):
    """Coördinator die data ophaalt van het TESO portaal."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialiseer de coördinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="TESO",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]

    async def _async_update_data(self) -> list[dict]:
        """Haal data op van het TESO portaal."""
        try:
            return await self._fetch_passes()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Fout bij ophalen TESO data: {err}") from err

    async def _fetch_passes(self) -> list[dict]:
        """Login en haal pasgegevens op."""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(ssl=True)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            cookie_jar=aiohttp.CookieJar(),
        ) as session:
            # Stap 1: haal de loginpagina op om het CSRF token te krijgen
            async with session.get(LOGIN_URL) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Kon loginpagina niet ophalen: {resp.status}")
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
            if not csrf_input:
                raise UpdateFailed("Kon CSRF token niet vinden op loginpagina")
            csrf_token = csrf_input["value"]

            # Stap 2: login
            login_data = {
                "csrfmiddlewaretoken": csrf_token,
                "username": self.username,
                "password": self.password,
            }
            headers = {
                "Referer": LOGIN_URL,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            async with session.post(
                LOGIN_URL, data=login_data, headers=headers, allow_redirects=True
            ) as resp:
                if resp.status not in (200, 302):
                    raise UpdateFailed(f"Login mislukt: {resp.status}")

                # Controleer of we zijn ingelogd door te kijken of we op my-teso zijn
                final_url = str(resp.url)
                if "login" in final_url:
                    raise ConfigEntryAuthFailed(
                        "Inloggen mislukt: controleer gebruikersnaam en wachtwoord"
                    )

            # Stap 3: haal de passenpagina op
            async with session.get(PASSES_URL) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Kon passenpagina niet ophalen: {resp.status}")
                html = await resp.text()

            return self._parse_passes(html)

    def _parse_passes(self, html: str) -> list[dict]:
        """Parseer de HTML en extraheer pasgegevens."""
        soup = BeautifulSoup(html, "html.parser")
        passes = []

        for card in soup.find_all("div", class_="card-row-container"):
            pass_data = {}

            # Pasnummer
            card_number_el = card.find("span", class_="teso-card-row-header__card-number")
            if card_number_el:
                pass_data["card_number"] = card_number_el.text.strip()

            # Kenteken (kan leeg zijn voor e-tickets)
            plate_el = card.find("span", class_="uppercase")
            if plate_el:
                pass_data["license_plate"] = plate_el.text.strip()

            # Voertuigomschrijving (bijv. "Volvo")
            personal_el = card.find("p", class_="personalinfo")
            if personal_el:
                pass_data["vehicle"] = personal_el.text.strip()

            # Producten op de pas
            products = []
            for row in card.find_all("div", class_="table-row-product"):
                product = {}

                name_el = row.find("div", class_="ticket_name")
                if name_el:
                    product["name"] = name_el.text.strip()

                retours_el = row.find("div", class_="table-row-retours")
                if retours_el:
                    try:
                        product["remaining"] = int(retours_el.text.strip())
                    except ValueError:
                        product["remaining"] = 0

                if product:
                    products.append(product)

            pass_data["products"] = products

            if pass_data.get("products"):
                passes.append(pass_data)

        _LOGGER.debug("TESO: gevonden passen: %s", passes)
        return passes
