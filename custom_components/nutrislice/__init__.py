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
    DEFAULT_CATEGORIES,
    DOMAIN,
)
from .coordinator import NutrisliceDataUpdateCoordinator
from .model import NutrisliceConfig

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nutrislice from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    categories = entry.options.get(
        CONF_CATEGORIES, entry.data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES)
    )

    coordinator = NutrisliceDataUpdateCoordinator(
        hass,
        NutrisliceConfig(
            district=entry.data[CONF_DISTRICT],
            school_name=entry.data[CONF_SCHOOL_NAME],
            meal_type=entry.data[CONF_MEAL_TYPE],
            categories=categories,
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
