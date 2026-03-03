"""Calendar platform for nutrislice."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import NutrisliceDataUpdateCoordinator
from .model import NutrisliceConfig, Day

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
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

        self._attr_unique_id = (
            f"nutrislice_{self.config.district}_{self.config.school_name}_"
            f"{self.config.meal_type}_calendar"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Nutrislice instance."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"nutrislice_{self.config.district}_{self.config.school_name}_{self.config.meal_type}",
                )
            },
            name=f"{self.config.school_name.replace('-', ' ').title()} {self.config.meal_type.title()}",
            manufacturer="Nutrislice",
            model="School Menu",
        )

    def _day_to_event(self, day: Day) -> CalendarEvent | None:
        """Convert a Nutrislice Day into a CalendarEvent."""
        if not day.menu_items:
            return None

        # Check for holiday
        holiday = next((i for i in day.menu_items if i.is_holiday), None)
        if holiday:
            return CalendarEvent(
                summary=f"Holiday: {holiday.text}",
                start=day.date,
                end=day.date + timedelta(days=1),
                description="No school meal service.",
            )

        # Build description from valid foods
        foods = [i.food for i in day.menu_items if i.food]
        if not foods:
            return None

        description_lines = []
        for category in sorted(list(set(f.food_category.value for f in foods))):
            items_in_cat = [f.name for f in foods if f.food_category.value == category]
            if items_in_cat:
                description_lines.append(
                    f"{category.title()}: {', '.join(items_in_cat)}"
                )

        return CalendarEvent(
            summary=f"Menu: {len(foods)} items",
            start=day.date,
            end=day.date + timedelta(days=1),
            description="\n".join(description_lines),
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming calendar event."""
        if not self.coordinator.data:
            return None

        today = datetime.now().date()
        for week in self.coordinator.data.values():
            if not week:
                continue
            for day in week.days:
                if day.date >= today:
                    event = self._day_to_event(day)
                    if event:
                        return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        events = []
        start_d = start_date.date()
        end_d = end_date.date()

        for week in self.coordinator.data.values():
            if not week:
                continue
            for day in week.days:
                if start_d <= day.date <= end_d:
                    event = self._day_to_event(day)
                    if event:
                        events.append(event)

        return events
