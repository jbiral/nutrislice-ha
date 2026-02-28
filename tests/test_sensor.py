"""Test the Nutrislice sensor."""

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.nutrislice.sensor import NutrisliceSensor
from custom_components.nutrislice.coordinator import NutrisliceDataUpdateCoordinator
from custom_components.nutrislice.model import NutrisliceConfig
from unittest.mock import patch, AsyncMock
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_component import async_update_entity


async def test_sensor_state_and_attributes(
    hass, freezer, mock_nutrislice_data_validated
):
    """Test the sensor parses data correctly."""

    freezer.move_to("2026-02-17")

    with patch(
        "custom_components.nutrislice.coordinator.NutrisliceDataUpdateCoordinator._async_update_data",
        new_callable=AsyncMock,
        return_value=mock_nutrislice_data_validated,
    ):
        mock_entry = MockConfigEntry(
            domain="nutrislice",
            data={
                "district": "my-district",
                "school_name": "elementary-school",
                "meal_type": "lunch",
                "categories": ["entree", "fruit"],
            },
            entry_id="test_123",
        )
        mock_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

        # Test sensor was registered properly
        state = hass.states.get("sensor.elementary_school_lunch")
        assert state is not None

        # Verify sensor unique id
        entry = entity_registry.async_get(hass).async_get(
            "sensor.elementary_school_lunch"
        )
        assert entry.unique_id == "nutrislice_my-district_elementary-school_lunch"

        # Verify sensor state and attributes
        assert state.state == "2 Entrees Available"
        assert state.attributes.get("friendly_name") == "Elementary School Lunch"
        assert state.attributes.get("district") == "my-district"
        assert state.attributes.get("school_name") == "elementary-school"
        assert state.attributes.get("meal_type") == "lunch"
        assert state.attributes.get("categories") == ["entree", "fruit"]

        assert state.attributes.get("days")[0]["date"] == "2026-02-16"
        assert state.attributes.get("days")[0]["is_holiday"] is True
        assert state.attributes.get("days")[0]["holiday_name"] == "Presidents Day"
        assert state.attributes.get("days")[1]["date"] == "2026-02-17"

        assert state.attributes.get("days")[1]["date"] == "2026-02-17"
        assert state.attributes.get("days")[1]["is_holiday"] is False
        assert state.attributes.get("days")[1]["has_menu"] is True
        assert len(state.attributes.get("days")[1]["menu_items"]) == 3
        assert state.attributes.get("days")[1]["menu_items"][0]["name"] == "Pizza"
        assert state.attributes.get("days")[1]["menu_items"][0]["category"] == "entree"
        assert state.attributes.get("days")[1]["menu_items"][2]["name"] == "Apple"
        assert state.attributes.get("days")[1]["menu_items"][2]["category"] == "fruit"

        freezer.move_to("2026-02-16")
        await async_update_entity(hass, "sensor.elementary_school_lunch")
        state = hass.states.get("sensor.elementary_school_lunch")

        assert state.state == "Presidents Day"

        freezer.move_to("2026-02-15")
        await async_update_entity(hass, "sensor.elementary_school_lunch")
        state = hass.states.get("sensor.elementary_school_lunch")

        assert state.state == "unknown"


async def test_set_date_service(hass, freezer, mock_nutrislice_data_validated):
    """Test the set_date service updates the sensor's target date."""
    freezer.move_to("2026-02-17")

    with patch(
        "custom_components.nutrislice.coordinator.NutrisliceDataUpdateCoordinator._async_update_data",
        new_callable=AsyncMock,
        return_value=mock_nutrislice_data_validated,
    ):
        mock_entry = MockConfigEntry(
            domain="nutrislice",
            data={
                "district": "my-district",
                "school_name": "elementary-school",
                "meal_type": "lunch",
                "categories": ["entree"],
            },
            entry_id="test_set_date",
        )
        mock_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

        # Initial state (2026-02-17)
        state = hass.states.get("sensor.elementary_school_lunch")
        assert state.attributes.get("target_date") == "2026-02-17"

        # Call service to set date to tomorrow
        await hass.services.async_call(
            "nutrislice",
            "set_date",
            {"entity_id": "sensor.elementary_school_lunch", "date": "tomorrow"},
            blocking=True,
        )
        state = hass.states.get("sensor.elementary_school_lunch")
        assert state.attributes.get("target_date") == "2026-02-18"

        # Call service with specific date
        await hass.services.async_call(
            "nutrislice",
            "set_date",
            {"entity_id": "sensor.elementary_school_lunch", "date": "2026-02-16"},
            blocking=True,
        )
        state = hass.states.get("sensor.elementary_school_lunch")
        assert state.attributes.get("target_date") == "2026-02-16"
        assert state.state == "Presidents Day"
