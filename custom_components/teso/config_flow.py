"""Config flow voor de TESO integratie."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from bs4 import BeautifulSoup

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

LOGIN_URL = "https://www.teso.nl/my-teso/login/"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_credentials(username: str, password: str) -> bool:
    """Valideer de inloggegevens bij TESO."""
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout,
        cookie_jar=aiohttp.CookieJar(),
    ) as session:
        # Haal CSRF token op
        async with session.get(LOGIN_URL) as resp:
            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if not csrf_input:
            return False
        csrf_token = csrf_input["value"]

        # Probeer in te loggen
        login_data = {
            "csrfmiddlewaretoken": csrf_token,
            "username": username,
            "password": password,
        }
        headers = {
            "Referer": LOGIN_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with session.post(
            LOGIN_URL, data=login_data, headers=headers, allow_redirects=True
        ) as resp:
            final_url = str(resp.url)
            return "login" not in final_url


class TesoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow voor TESO."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Verwerk de gebruikersinvoer."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                valid = await validate_credentials(username, password)
                if valid:
                    await self.async_set_unique_id(username)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"TESO ({username})",
                        data=user_input,
                    )
                else:
                    errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Onverwachte fout bij validatie")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
