"""Config flow for Nutrislice integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CATEGORIES,
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DEFAULT_CATEGORIES,
    DEFAULT_MEAL_TYPE,
    DOMAIN,
    MEAL_TYPES,
    CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DISTRICT): str,
        vol.Required(CONF_SCHOOL_NAME): str,
        vol.Required(CONF_MEAL_TYPE, default=DEFAULT_MEAL_TYPE): vol.In(MEAL_TYPES),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    district = data[CONF_DISTRICT].strip().lower()
    school_name = data[CONF_SCHOOL_NAME].strip().lower()
    meal_type = data[CONF_MEAL_TYPE].strip().lower()

    # Use a dummy date to validate the API connection
    url = f"https://{district}.api.nutrislice.com/menu/api/weeks/school/{school_name}/menu-type/{meal_type}/2023/01/01/?format=json"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to fetch Nutrislice data: %s", response.status)
                    raise InvalidAuth(f"Could not connect to Nutrislice API ({response.status}). Check District/School Name.")
                json_data = await response.json()
                if not json_data.get("days"):
                     raise InvalidAuth("Invalid data received. Check District/School Name.")
        except (InvalidAuth, CannotConnect):
            raise
        except aiohttp.ClientError as err:
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during validation")
            raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {
        "title": f"Nutrislice: {school_name.replace('-', ' ').title()} - {meal_type.title()}"
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nutrislice."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._title: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step where user enters district and school."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self._data = {
                    CONF_DISTRICT: user_input[CONF_DISTRICT].strip().lower(),
                    CONF_SCHOOL_NAME: user_input[CONF_SCHOOL_NAME].strip().lower(),
                    CONF_MEAL_TYPE: user_input[CONF_MEAL_TYPE].strip().lower(),
                }
                self._title = info["title"]
                
                return await self.async_step_categories()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_categories(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the category selection step."""
        if user_input is not None:
            self._data[CONF_CATEGORIES] = user_input[CONF_CATEGORIES]
            
            # Add a unique ID to prevent adding the same school/meal twice
            await self.async_set_unique_id(
                f"{self._data[CONF_DISTRICT]}_{self._data[CONF_SCHOOL_NAME]}_{self._data[CONF_MEAL_TYPE]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=self._title, data=self._data)

        # Build categorization schema
        # We use a MultiSelect for easy checkbox selection in HA
        category_options = {cat: cat.title() for cat in CATEGORIES}
        
        schema = vol.Schema({
            vol.Required(CONF_CATEGORIES, default=DEFAULT_CATEGORIES): vol.All(
                cv.ensure_list, [vol.In(CATEGORIES)]
            ),
        })
        
        # Note: In standard HA config flow, MultiSelect often uses a selector
        # But for simplicity with voluptuous:
        data_schema = vol.Schema({
            vol.Required(CONF_CATEGORIES, default=DEFAULT_CATEGORIES): cv.multi_select(category_options)
        })

        return self.async_show_form(
            step_id="categories", data_schema=data_schema
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth (invalid district/school)."""
