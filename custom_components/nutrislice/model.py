"""Pydantic data models for the Nutrislice integration."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .const import DEFAULT_CATEGORIES, expand_category_aliases

MAX_STATE_LENGTH = 255


def _clean_str(value: Any) -> str:
    """Normalize optional or arbitrary string values from the API."""
    if value is None:
        return ""
    return str(value).strip()


def _normalize_category(value: Any) -> str:
    """Normalize category strings to lowercase without failing on unknown values."""
    if value is None:
        return ""
    if isinstance(value, StrEnum):
        return value.value
    return str(value).strip().lower()


CleanStr = Annotated[str, BeforeValidator(_clean_str)]
CategoryStr = Annotated[str, BeforeValidator(_normalize_category)]


class Category(StrEnum):
    """Known Nutrislice food categories."""

    EMPTY = ""
    ENTREE = "entree"
    SIDES = "sides"
    SIDE = "side"
    DESSERT = "dessert"
    DRINK = "drink"
    BREAKFAST = "breakfast"
    SNACK = "snack"
    CONDIMENT = "condiment"
    FRUIT = "fruit"
    VEGETABLE = "vegetable"
    GRAIN = "grain"
    BEVERAGE = "beverage"
    MILK = "milk"
    MEAT = "meat"


class NutrisliceConfig(BaseModel):
    """Represents a validated Nutrislice configuration."""

    model_config = ConfigDict(extra="ignore")

    district: CleanStr
    school_name: CleanStr
    meal_type: CleanStr
    categories: list[CategoryStr] = Field(
        default_factory=lambda: list(DEFAULT_CATEGORIES)
    )

    @property
    def unique_id(self) -> str:
        """Return the base unique ID for this school and meal type."""
        return f"nutrislice_{self.district}_{self.school_name}_{self.meal_type}"

    @property
    def device_name(self) -> str:
        """Return the human-readable device name."""
        return f"{self.school_name.replace('-', ' ').title()} {self.meal_type.title()}"

    @property
    def primary_category(self) -> str:
        """Return the primary category used for the sensor state."""
        return self.categories[0] if self.categories else Category.ENTREE.value


class Food(BaseModel):
    """Represents a food item inside a Nutrislice menu item."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    name: CleanStr = ""
    description: CleanStr = ""
    subtext: CleanStr = ""
    food_category: CategoryStr = ""

    @property
    def is_valid_menu_food(self) -> bool:
        """Return True if this food has a real displayable name."""
        return bool(self.name and self.name.lower() != "menu subject to change")


class MenuItem(BaseModel):
    """Represents a single entry on a daily menu (food item, holiday, or header)."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    position: int | str | None = None
    is_section_title: bool = False
    is_holiday: bool = False
    text: CleanStr = ""
    category: CategoryStr = ""
    food: Food | None = None
    serving_size_amount: float | int | str | None = None
    serving_size_unit: CleanStr = ""

    @property
    def effective_category(self) -> str:
        """Return the item's category, falling back to the nested food's category.

        If a valid food item has an empty category in Nutrislice (common when
        school staff omit the category tag on main dishes), default to 'entree'.
        """
        if self.category:
            return self.category
        if self.food and self.food.food_category:
            return self.food.food_category
        if not self.is_holiday and self.food and self.food.is_valid_menu_food:
            return Category.ENTREE.value
        return ""

    def matches_categories(self, allowed_categories: Iterable[str]) -> bool:
        """Return True if this item's category matches any of the allowed categories."""
        cat = self.effective_category
        if not cat:
            return False
        expanded = expand_category_aliases(allowed_categories)
        return cat in expanded


class Day(BaseModel):
    """Represents a single calendar day in the Nutrislice schedule."""

    model_config = ConfigDict(extra="ignore")

    date: date
    menu_items: list[MenuItem] = Field(default_factory=list)

    @property
    def holiday_item(self) -> MenuItem | None:
        """Return the holiday menu item if this day is a school holiday."""
        return next((item for item in self.menu_items if item.is_holiday), None)

    @property
    def is_holiday(self) -> bool:
        """Return True if this day is marked as a holiday."""
        return self.holiday_item is not None

    @property
    def holiday_name(self) -> str | None:
        """Return the holiday name if this day is a holiday."""
        if item := self.holiday_item:
            return item.text or "Holiday"
        return None

    @property
    def valid_menu_items(self) -> list[MenuItem]:
        """Return non-holiday menu items that have a valid food object."""
        return [
            item
            for item in self.menu_items
            if not item.is_holiday and item.food and item.food.is_valid_menu_food
        ]

    @property
    def valid_foods(self) -> list[Food]:
        """Return all valid Food objects for this day."""
        return [item.food for item in self.valid_menu_items if item.food is not None]

    def get_items_for_category(self, category: str) -> list[MenuItem]:
        """Return valid menu items matching the target category (with aliases)."""
        return [
            item
            for item in self.valid_menu_items
            if item.matches_categories([category])
        ]

    def items_grouped_by_category(self) -> dict[str, list[str]]:
        """Return food names grouped by their effective category."""
        grouped: dict[str, list[str]] = {}
        for item in self.valid_menu_items:
            if item.food is None:
                continue
            cat = item.effective_category or "other"
            grouped.setdefault(cat, []).append(item.food.name)
        return grouped

    def format_state_value(self, primary_category: str) -> str:
        """Format the primary sensor state for this day (capped to HA's 255-char limit)."""
        if self.is_holiday:
            return (self.holiday_name or "Holiday")[:MAX_STATE_LENGTH]

        primary_items = [
            item.food.name
            for item in self.get_items_for_category(primary_category)
            if item.food is not None
        ]
        if primary_items:
            text = ", ".join(primary_items)
        elif self.valid_foods:
            text = ", ".join(food.name for food in self.valid_foods)
        else:
            return "No menu"

        if len(text) > MAX_STATE_LENGTH:
            return f"{text[: MAX_STATE_LENGTH - 3]}..."
        return text

    @property
    def menu_summary(self) -> str:
        """Return a human-readable summary of all items on the day's menu."""
        if self.is_holiday:
            return self.holiday_name or "Holiday"
        foods = self.valid_foods
        if foods:
            return ", ".join(food.name for food in foods)
        return "No menu"


class NutrisliceResponse(BaseModel):
    """The root object in a weekly Nutrislice API response."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    start_date: date | None = None
    last_updated: datetime | str | None = None
    days: list[Day] = Field(default_factory=list)

    def filter_categories(
        self, allowed_categories: Iterable[str]
    ) -> NutrisliceResponse:
        """Filter menu items in-place to keep holidays and configured categories."""
        allowed_list = list(allowed_categories)
        if not allowed_list:
            return self

        for day in self.days:
            day.menu_items = [
                item
                for item in day.menu_items
                if item.is_holiday or item.matches_categories(allowed_list)
            ]
        return self
