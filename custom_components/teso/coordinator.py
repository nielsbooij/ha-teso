"""Data coordinator voor de TESO integratie."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

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
TRIPS_URL = f"{BASE_URL}/my-teso/trips/"

UPDATE_INTERVAL = timedelta(minutes=5)


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
            return await self._fetch_data()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Fout bij ophalen TESO data: {err}") from err

    async def _fetch_data(self) -> list[dict]:
        """Login en haal alle gegevens op."""
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=aiohttp.CookieJar(),
        ) as session:
            # Stap 1: haal CSRF token op
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
                final_url = str(resp.url)
                if "login" in final_url:
                    raise ConfigEntryAuthFailed(
                        "Inloggen mislukt: controleer gebruikersnaam en wachtwoord"
                    )

            # Stap 3: haal passenpagina op
            async with session.get(PASSES_URL) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Kon passenpagina niet ophalen: {resp.status}")
                passes_html = await resp.text()

            # Stap 4: haal overtochten pagina op
            async with session.get(TRIPS_URL) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Kon overtochten pagina niet ophalen: {resp.status}")
                trips_html = await resp.text()

            passes = self._parse_passes(passes_html)
            trips = self._parse_trips(trips_html)

            # Koppel de laatste overtocht aan de juiste pas
            for pass_data in passes:
                card_number = pass_data.get("card_number", "")
                pass_data["last_trip"] = trips.get(card_number)

            return passes

    def _parse_passes(self, html: str) -> list[dict]:
        """Parseer de HTML van de passenpagina."""
        soup = BeautifulSoup(html, "html.parser")
        passes = []

        for card in soup.find_all("div", class_="card-row-container"):
            pass_data = {}

            # Pasnummer
            card_number_el = card.find("span", class_="teso-card-row-header__card-number")
            if card_number_el:
                pass_data["card_number"] = card_number_el.text.strip()

            # Kenteken
            plate_el = card.find("span", class_="uppercase")
            if plate_el:
                pass_data["license_plate"] = plate_el.text.strip()

            # Voertuig
            personal_el = card.find("p", class_="personalinfo")
            if personal_el:
                pass_data["vehicle"] = personal_el.text.strip()

            # Producten
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

            if pass_data.get("card_number"):
                passes.append(pass_data)

        _LOGGER.debug("TESO passen: %s", passes)
        return passes

    def _parse_trips(self, html: str) -> dict[str, datetime]:
        """Parseer de overtochten pagina en geef de laatste overtocht per pasnummer terug."""
        soup = BeautifulSoup(html, "html.parser")
        last_trips: dict[str, datetime] = {}

        dates = soup.find_all("p", class_="checkin-date")
        times = soup.find_all("p", class_="checkin-time")
        card_types = soup.find_all("p", class_="checkin-type")

        for date_el, time_el, card_el in zip(dates, times, card_types):
            card_text = card_el.get_text(separator=" ", strip=True)

            if "Pas:" in card_text:
                parts = card_text.split("Pas:")
                if len(parts) > 1:
                    card_number = parts[1].strip().split()[0]
                else:
                    continue
            else:
                continue

            # Alleen de eerste (meest recente) per pasnummer
            if card_number in last_trips:
                continue

            date_str = date_el.text.strip()
            time_str = time_el.text.strip().split(",")[0].strip()

            try:
                date_part = date_str.split(" om ")[0]
                clean_date = date_part.split()[-1]  # pakt "03-05-2026"
                clean_time = time_str  # time_str is al correct: "11:23"
                trip_dt = datetime.strptime(
                    f"{clean_date} {clean_time}", "%d-%m-%Y %H:%M"
                )
                last_trips[card_number] = trip_dt
            except ValueError:
                _LOGGER.warning("Kon datum niet verwerken: %s %s", date_str, time_str)

        _LOGGER.debug("TESO laatste overtochten: %s", last_trips)
        return last_trips
