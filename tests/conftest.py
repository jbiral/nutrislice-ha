"""Global fixtures for Nutrislice integration."""

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch(
        "custom_components.nutrislice.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


# TODO: replace with real data from API
@pytest.fixture
def mock_nutrislice_data():
    """Return a standard Nutrislice API response."""
    return {
        "current_week": {
            "days": [
                {
                    "date": "2026-02-16",
                    "menu_items": [
                        {
                            "is_holiday": True,
                            "text": "Presidents Day",
                        }
                    ],
                },
                {
                    "date": "2026-02-17",
                    "menu_items": [
                        {
                            "is_holiday": False,
                            "food": {
                                "food_category": "entree",
                                "name": "Pizza",
                                "description": "Cheese Pizza",
                            },
                        },
                        {
                            "is_holiday": False,
                            "food": {
                                "food_category": "entree",
                                "name": "Burger",
                                "description": "Hamburger",
                            },
                        },
                        {
                            "is_holiday": False,
                            "food": {
                                "food_category": "fruit",
                                "name": "Apple",
                            },
                        },
                    ],
                },
            ]
        },
        "next_week": None,
    }
