"""Constants for the Nutrislice integration."""

from datetime import timedelta
import logging

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
]

DEFAULT_CATEGORIES = ["entree"]
