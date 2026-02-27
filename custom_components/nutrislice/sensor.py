"""Sensor platform for nutrislice."""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CATEGORIES,
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DEFAULT_CATEGORIES,
    DOMAIN,
)
from .coordinator import NutrisliceDataUpdateCoordinator
from .model import NutrisliceConfig, Day, MenuItem, Category

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NutrisliceSensor(coordinator, entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_date",
        {vol.Required("date"): str},
        "set_target_date",
    )


class NutrisliceSensor(
    CoordinatorEntity[NutrisliceDataUpdateCoordinator], SensorEntity
):
    """Representation of a Nutrislice Sensor.

    This sensor displays the available menu items for a specific school and meal type.
    The primary state reflects the number of items in the first selected category (usually 'entree').
    Detailed menu information is available in the extra state attributes.
    """

    def __init__(
        self,
        coordinator: NutrisliceDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.config = NutrisliceConfig(
            district=entry.data[CONF_DISTRICT],
            school_name=entry.data[CONF_SCHOOL_NAME],
            meal_type=entry.data[CONF_MEAL_TYPE],
            categories=entry.data[CONF_CATEGORIES],
        )

        self._attr_name = f"{self.config.school_name.replace('-', ' ').title()} {self.config.meal_type.title()}"
        self._attr_unique_id = f"nutrislice_{self.config.district}_{self.config.school_name}_{self.config.meal_type}"
        self._attr_icon = "mdi:food-apple"
        self._target_date: date | None = None

    async def set_target_date(self, date_str: str) -> None:
        """Handle the service call to set the target date."""
        today = date.today()
        if date_str.lower() == "today":
            self._target_date = today
        elif date_str.lower() == "tomorrow":
            self._target_date = today + timedelta(days=1)
        else:
            try:
                self._target_date = date.fromisoformat(date_str)
            except ValueError:
                _LOGGER.error("Invalid date format: %s. Use YYYY-MM-DD", date_str)
                return

        self.async_write_ha_state()

    @property
    def _active_date(self) -> date:
        """Determine the date currently being displayed by the sensor."""
        if self._target_date:
            return self._target_date

        now = datetime.now()
        # After 1 PM, switch to showing tomorrow's menu
        if now.hour >= 13:
            return now.date() + timedelta(days=1)
        return now.date()

    def _get_all_days(self) -> list[Day]:
        """Collect and deduplicate days from the coordinator's Pydantic objects."""
        if not self.coordinator.data:
            return []

        unique_days: dict[date, Day] = {}
        for week in self.coordinator.data.values():
            if week is None:
                continue
            for day in week.days:
                if day.date not in unique_days:
                    unique_days[day.date] = day

        return [unique_days[d] for d in sorted(unique_days.keys())]

    def _get_items_for_category(self, day: Day, target_cat: str) -> list[MenuItem]:
        """Filter menu items based on category using the Pydantic Enum."""
        # Map the string from config to the Pydantic Enum
        try:
            enum_cat = Category(target_cat.lower())
        except ValueError:
            return []

        return [
            item
            for item in day.menu_items
            if item.food and item.food.food_category == enum_cat
        ]

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor (e.g., '2 Entrees Available' or 'Presidents Day')."""
        if not self.coordinator.data:
            return None

        target = self._active_date
        main_cat = self.config.categories[0] if self.config.categories else "entree"

        for day in self._get_all_days():
            if day.date == target:
                # 1. Check for Holiday
                holiday = next((i.text for i in day.menu_items if i.is_holiday), None)
                if holiday:
                    return holiday

                # 2. Count specific categories
                items = self._get_items_for_category(day, main_cat)
                if items:
                    return f"{len(items)} {main_cat.title()}s Available"

                return f"No {main_cat.title()}s/Weekend"

        return "unknown"

    def _format_day_for_attrs(self, day: Day) -> dict[str, Any]:
        """Convert a Day model into a dictionary for extra_state_attributes."""
        holiday_item = next((i for i in day.menu_items if i.is_holiday), None)

        menu_items = [
            {"name": i.food.name, "category": i.food.food_category.value}
            for i in day.menu_items
            if i.food
        ]

        return {
            "date": day.date.isoformat(),
            "is_holiday": holiday_item is not None,
            "holiday_name": holiday_item.text if holiday_item else None,
            "menu_items": menu_items,
            "has_menu": len(menu_items) > 0,
            "menu_summary": (
                holiday_item.text
                if holiday_item
                else (
                    ", ".join(i["name"] for i in menu_items)
                    if menu_items
                    else "No menu"
                )
            ),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes using Pydantic-processed data."""
        days = self._get_all_days()
        parsed_days = [self._format_day_for_attrs(d) for d in days]

        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

        def find_summary(d_str: str) -> str:
            return next(
                (d["menu_summary"] for d in parsed_days if d["date"] == d_str),
                "No menu",
            )

        return {
            "target_date": self._active_date.isoformat(),
            "district": self.config.district,
            "school_name": self.config.school_name,
            "meal_type": self.config.meal_type,
            "categories": self.config.categories,
            "today_menu": find_summary(today_str),
            "tomorrow_menu": find_summary(tomorrow_str),
            "days": parsed_days,
        }
