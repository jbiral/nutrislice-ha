"""The Nutrislice integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CATEGORIES,
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DOMAIN,
)
from .coordinator import NutrisliceDataUpdateCoordinator
from .model import NutrisliceConfig

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nutrislice from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = NutrisliceDataUpdateCoordinator(
        hass,
        NutrisliceConfig(
            district=entry.data[CONF_DISTRICT],
            school_name=entry.data[CONF_SCHOOL_NAME],
            meal_type=entry.data[CONF_MEAL_TYPE],
            categories=entry.data[CONF_CATEGORIES],
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
