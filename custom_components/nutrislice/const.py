"""Constants for the Nutrislice integration."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import timedelta

DOMAIN = "nutrislice"
LOGGER = logging.getLogger(__name__)

CONF_DISTRICT = "district"
CONF_SCHOOL_NAME = "school_name"
CONF_MEAL_TYPE = "meal_type"
CONF_CATEGORIES = "categories"

# Default values
DEFAULT_MEAL_TYPE = "lunch"
MEAL_TYPES = ["lunch", "breakfast"]

# Update interval
SCAN_INTERVAL = timedelta(hours=6)

# Categories available in Nutrislice
CATEGORIES = [
    "entree",
    "sides",
    "dessert",
    "drink",
    "breakfast",
    "snack",
    "condiment",
    "fruit",
    "vegetable",
    "grain",
    "beverage",
    "milk",
    "meat",
]

DEFAULT_CATEGORIES = ["entree"]

# Flexible category aliases to handle district-specific naming variations
CATEGORY_ALIASES: dict[str, set[str]] = {
    "entree": {"entree", "entrees"},
    "sides": {"sides", "side"},
    "side": {"sides", "side"},
    "drink": {"drink", "drinks", "beverage", "beverages", "milk"},
    "beverage": {"drink", "drinks", "beverage", "beverages", "milk"},
    "vegetable": {"vegetable", "vegetables", "veggie", "veggies"},
    "fruit": {"fruit", "fruits"},
    "grain": {"grain", "grains"},
    "condiment": {"condiment", "condiments"},
    "dessert": {"dessert", "desserts"},
    "snack": {"snack", "snacks"},
}


def expand_category_aliases(categories: Iterable[str]) -> set[str]:
    """Expand a collection of category names with known aliases."""
    expanded: set[str] = set()
    for cat in categories:
        normalized = cat.strip().lower()
        if not normalized:
            continue
        expanded.add(normalized)
        if normalized in CATEGORY_ALIASES:
            expanded.update(CATEGORY_ALIASES[normalized])
    return expanded
