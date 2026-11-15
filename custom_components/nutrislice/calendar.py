"""Calendar platform for Nutrislice."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import NutrisliceDataUpdateCoordinator
from .model import Day

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform from a config entry."""
    coordinator: NutrisliceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NutrisliceCalendar(coordinator, entry)])


class NutrisliceCalendar(
    CoordinatorEntity[NutrisliceDataUpdateCoordinator], CalendarEntity
):
    """Representation of a Nutrislice Calendar."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self,
        coordinator: NutrisliceDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self.entry = entry
        self.config = coordinator.config
        self._attr_unique_id = f"{self.config.unique_id}_calendar"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Nutrislice instance."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.config.unique_id)},
            name=self.config.device_name,
            manufacturer="Nutrislice",
            model="School Menu",
        )

    def _day_to_event(self, day: Day) -> CalendarEvent | None:
        """Convert a Nutrislice Day into a CalendarEvent."""
        if not day.menu_items:
            return None

        if day.is_holiday:
            return CalendarEvent(
                summary=f"Holiday: {day.holiday_name}",
                start=day.date,
                end=day.date + timedelta(days=1),
                description="No school meal service.",
            )

        valid_items = day.valid_menu_items
        if not valid_items:
            return None

        categories = sorted(
            {item.effective_category or "other" for item in valid_items}
        )
        description_lines = []
        for category in categories:
            items_in_cat = [
                item.food.name
                for item in valid_items
                if item.food and (item.effective_category or "other") == category
            ]
            if items_in_cat:
                description_lines.append(
                    f"{category.title()}: {', '.join(items_in_cat)}"
                )

        return CalendarEvent(
            summary=f"Menu: {len(valid_items)} items",
            start=day.date,
            end=day.date + timedelta(days=1),
            description="\n".join(description_lines),
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming calendar event."""
        if not self.coordinator.data:
            return None

        today = dt_util.now().date()
        for day in self.coordinator.get_all_days():
            if day.date >= today:
                if event := self._day_to_event(day):
                    return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        events: list[CalendarEvent] = []
        start_d = start_date.date()
        end_d = end_date.date()

        for day in self.coordinator.get_all_days():
            if start_d <= day.date <= end_d:
                if event := self._day_to_event(day):
                    events.append(event)

        return events
