"""Sensor platform for nutrislice."""
from __future__ import annotations
from datetime import datetime, timedelta

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import voluptuous as vol

from .const import CONF_CATEGORIES, CONF_DISTRICT, CONF_MEAL_TYPE, CONF_SCHOOL_NAME, DEFAULT_CATEGORIES, DOMAIN
from .coordinator import NutrisliceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NutrisliceSensor(
                coordinator,
                entry,
            )
        ]
    )

    platform = entity_platform.async_get_current_platform()

    # Register the set_date service for the sensor
    platform.async_register_entity_service(
        "set_date",
        {
            vol.Required("date"): str,
        },
        "set_target_date",
    )


class NutrisliceSensor(CoordinatorEntity[NutrisliceDataUpdateCoordinator], SensorEntity):
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
        self.district = entry.data[CONF_DISTRICT]
        self.school_name = entry.data[CONF_SCHOOL_NAME]
        self.meal_type = entry.data[CONF_MEAL_TYPE]
        self.categories = entry.data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES)
        
        self._attr_name = f"{self.school_name.replace('-', ' ').title()} {self.meal_type.title()}"
        self._attr_unique_id = f"nutrislice_{self.district}_{self.school_name}_{self.meal_type}"
        self._attr_icon = "mdi:food-apple"
        self._target_date: str | None = None

    async def set_target_date(self, date: str) -> None:
        """Handle the service call to set the target date for this sensor."""
        if date.lower() == "today":
            self._target_date = datetime.now().strftime("%Y-%m-%d")
        elif date.lower() == "tomorrow":
            self._target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            self._target_date = date
            
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return the state of the sensor.
        
        Shows the number of available items for the first selected category.
        """
        if not self.coordinator.data:
            return "unavailable"
            
        if self._target_date:
            target_str = self._target_date
        else:
            today_str = datetime.now().strftime("%Y-%m-%d")
            # Automatically jump to tomorrow if past 1 PM
            if datetime.now().hour >= 13:
                 target_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                 target_str = today_str
        
        # Determine main category for the status string
        main_cat = self.categories[0] if self.categories else "entree"

        # Search for the target day
        for day in self._get_all_days():
            if day.get("date") == target_str:
                # Check if it's a holiday
                for item in day.get("menu_items", []):
                    if item.get("is_holiday"):
                        return item.get("text", "Holiday")
                        
                # Check for food in the primary category with flexible matching
                allowed_aliases = [main_cat]
                if main_cat == "sides":
                    allowed_aliases.extend(["vegetable", "fruit", "grain"])
                
                foods = []
                for item in day.get("menu_items", []):
                    if not item.get("food"):
                        continue
                    
                    # Correctly get category from item or its food
                    item_cat = item.get("category")
                    if not item_cat and item.get("food"):
                        item_cat = item["food"].get("food_category")
                    
                    cat = (item_cat or "").lower()
                    if not cat:
                        continue
                        
                    # Flexible matching: starts with or matches an alias
                    if any(cat.startswith(a) or a.startswith(cat) for a in allowed_aliases):
                        foods.append(item)
                if foods:
                    return f"{len(foods)} {main_cat.title()}s Available"
                else:
                     return f"No {main_cat.title()}s/Weekend"
                
        return "unknown"

    def _get_all_days(self) -> list[dict[str, Any]]:
        """Get a deduplicated and sorted list of all days from the coordinator."""
        if not self.coordinator.data:
            return []

        all_days_raw = []
        if self.coordinator.data.get("previous_week"):
             all_days_raw.extend(self.coordinator.data["previous_week"].get("days", []))
        if self.coordinator.data.get("current_week"):
             all_days_raw.extend(self.coordinator.data["current_week"].get("days", []))
        if self.coordinator.data.get("next_week"):
             all_days_raw.extend(self.coordinator.data["next_week"].get("days", []))

        # Deduplicate by date and sort
        unique_days = {}
        for day in all_days_raw:
            date_str = day.get("date")
            if date_str and date_str not in unique_days:
                unique_days[date_str] = day
        
        return [unique_days[d] for d in sorted(unique_days.keys())]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        parsed_days = []
        
        # Combine previous, current and next week days
        all_days = []
        if self.coordinator.data.get("previous_week"):
             all_days.extend(self.coordinator.data["previous_week"].get("days", []))
             
        if self.coordinator.data.get("current_week"):
             all_days.extend(self.coordinator.data["current_week"].get("days", []))
             
        if self.coordinator.data.get("next_week"):
             all_days.extend(self.coordinator.data["next_week"].get("days", []))

        from .const import CATEGORIES
        
        for day in self._get_all_days():
            date_str = day.get("date")
            if not date_str:
                continue
                
            day_data = {
                "date": date_str,
                "is_holiday": False,
                "holiday_name": None,
                "menu_items": [],
                "has_menu": False
            }
            
            for item in day.get("menu_items", []):
                if item.get("is_holiday"):
                    day_data["is_holiday"] = True
                    day_data["holiday_name"] = item.get("text", "Holiday")
                    break # Skip processing other items if it's a holiday

                category = item.get("category")
                if not category and item.get("food"):
                    category = item["food"].get("food_category")

                if category:
                    category = category.lower()

                if item.get("food"):
                    name = item["food"].get("name", "").strip()
                    # Filter out useless ones
                    if name and name != "Menu Subject to Change":
                        day_data["menu_items"].append({
                            "name": name,
                            "category": category or "other",
                        })
                        day_data["has_menu"] = True
            
            if day_data["is_holiday"]:
                day_data["menu_summary"] = day_data["holiday_name"]
            elif day_data["menu_items"]:
                day_data["menu_summary"] = ", ".join([item["name"] for item in day_data["menu_items"]])
            else:
                day_data["menu_summary"] = "No menu"
            
            parsed_days.append(day_data)

        # Determine target date for the card
        if self._target_date:
            target_str = self._target_date
        else:
            if datetime.now().hour >= 13:
                 target_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                 target_str = datetime.now().strftime("%Y-%m-%d")

        today_str_abs = datetime.now().strftime("%Y-%m-%d")
        tomorrow_str_abs = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        today_menu = next((d["menu_summary"] for d in parsed_days if d["date"] == today_str_abs), "No menu")
        tomorrow_menu = next((d["menu_summary"] for d in parsed_days if d["date"] == tomorrow_str_abs), "No menu")

        return {
            "get_target_date": target_str, # Keep for existing logic if any
            "target_date": target_str,
            "district": self.district,
            "school_name": self.school_name,
            "meal_type": self.meal_type,
            "categories": self.categories,
            "today_menu": today_menu,
            "tomorrow_menu": tomorrow_menu,
            "days": parsed_days
        }
