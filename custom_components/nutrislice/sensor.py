"""Sensor platform for Nutrislice."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import NutrisliceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class NutrisliceSensorEntityDescription(SensorEntityDescription):
    """Describes a Nutrislice daily menu sensor entity."""

    day_offset: int


SENSOR_DESCRIPTIONS: tuple[NutrisliceSensorEntityDescription, ...] = (
    NutrisliceSensorEntityDescription(
        key="today",
        translation_key="today",
        name="Today",
        icon="mdi:food-apple",
        day_offset=0,
    ),
    NutrisliceSensorEntityDescription(
        key="tomorrow",
        translation_key="tomorrow",
        name="Tomorrow",
        icon="mdi:calendar-arrow-right",
        day_offset=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator: NutrisliceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NutrisliceSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class NutrisliceSensor(
    CoordinatorEntity[NutrisliceDataUpdateCoordinator], SensorEntity
):
    """Representation of a Nutrislice daily menu sensor (Today or Tomorrow).

    The primary state shows the comma-separated items in the primary category
    (e.g. 'Pizza, Burger'), the holiday name (e.g. 'Presidents Day'), or 'No menu'.
    The extra state attributes contain only that single day's categorized items,
    keeping database storage tiny (~200-350 bytes).
    """

    _attr_has_entity_name = True
    entity_description: NutrisliceSensorEntityDescription

    def __init__(
        self,
        coordinator: NutrisliceDataUpdateCoordinator,
        entry: ConfigEntry,
        description: NutrisliceSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.config = coordinator.config
        self.entity_description = description
        self._attr_unique_id = f"{self.config.unique_id}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._handle_midnight_update,
                hour=0,
                minute=0,
                second=0,
            )
        )

    @callback
    def _handle_midnight_update(self, _now: datetime) -> None:
        """Update sensor state at midnight when the target date rolls over."""
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Nutrislice instance."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.config.unique_id)},
            name=self.config.device_name,
            manufacturer="Nutrislice",
            model="School Menu",
        )

    @property
    def _target_date(self) -> date:
        """Return the target date for this sensor in the Home Assistant timezone."""
        return dt_util.now().date() + timedelta(days=self.entity_description.day_offset)

    @property
    def native_value(self) -> str | None:
        """Return the primary menu items, holiday name, or 'No menu'."""
        if not self.coordinator.data:
            return None

        day = self.coordinator.get_day(self._target_date)
        if day is None:
            return "No menu"

        return day.format_state_value(self.config.primary_category)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return compact state attributes for this single day."""
        if not self.coordinator.data:
            return {}

        target = self._target_date
        day = self.coordinator.get_day(target)

        return {
            "date": target.isoformat(),
            "is_holiday": day.is_holiday if day else False,
            "holiday_name": day.holiday_name if day else None,
            "menu_summary": day.menu_summary if day else "No menu",
            "items_by_category": day.items_grouped_by_category() if day else {},
        }
