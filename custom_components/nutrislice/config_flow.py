"""Config flow for Nutrislice integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    CATEGORIES,
    CONF_CATEGORIES,
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DEFAULT_CATEGORIES,
    DEFAULT_MEAL_TYPE,
    DOMAIN,
    MEAL_TYPES,
)
from .model import NutrisliceResponse

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DISTRICT): str,
        vol.Required(CONF_SCHOOL_NAME): str,
        vol.Required(CONF_MEAL_TYPE, default=DEFAULT_MEAL_TYPE): vol.In(MEAL_TYPES),
    }
)


def _build_categories_schema(default_categories: list[str]) -> vol.Schema:
    """Build the voluptuous schema for selecting food categories."""
    category_options = {cat: cat.title() for cat in CATEGORIES}
    return vol.Schema(
        {
            vol.Required(CONF_CATEGORIES, default=default_categories): cv.multi_select(
                category_options
            )
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    district = data[CONF_DISTRICT].strip().lower()
    school_name = data[CONF_SCHOOL_NAME].strip().lower()
    meal_type = data[CONF_MEAL_TYPE].strip().lower()

    today_path = dt_util.now().date().strftime("%Y/%m/%d")
    url = (
        f"https://{district}.api.nutrislice.com/menu/api/weeks/"
        f"school/{school_name}/menu-type/{meal_type}/{today_path}/?format=json"
    )

    session = async_get_clientsession(hass)
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                _LOGGER.error("Failed to fetch Nutrislice data: %s", response.status)
                raise InvalidAuth(
                    f"Could not connect to Nutrislice API ({response.status}). "
                    "Check District/School Name."
                )
            json_data = await response.json()
            validated = NutrisliceResponse.model_validate(json_data)
            if not validated.days:
                raise InvalidAuth("Invalid data received. Check District/School Name.")
    except (InvalidAuth, CannotConnect):
        raise
    except aiohttp.ClientError as err:
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from err

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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

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

            await self.async_set_unique_id(
                f"{self._data[CONF_DISTRICT]}_{self._data[CONF_SCHOOL_NAME]}_{self._data[CONF_MEAL_TYPE]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=self._title, data=self._data)

        return self.async_show_form(
            step_id="categories",
            data_schema=_build_categories_schema(DEFAULT_CATEGORIES),
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Nutrislice options for reconfiguring food categories."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_categories = self.config_entry.options.get(
            CONF_CATEGORIES,
            self.config_entry.data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_categories_schema(current_categories),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth (invalid district/school)."""
