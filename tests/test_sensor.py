"""Test the Nutrislice Today and Tomorrow sensors."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity_component import async_update_entity
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_sensor_today_and_tomorrow(hass, freezer, mock_nutrislice_data_validated):
    """Test Today and Tomorrow sensors parse state and attributes properly."""
    # Start on Sunday 2026-02-15 (Tomorrow is Presidents Day 2026-02-16)
    freezer.move_to("2026-02-15 10:00:00")

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

        ent_reg = entity_registry.async_get(hass)

        today_entry = ent_reg.async_get("sensor.elementary_school_lunch_today")
        tomorrow_entry = ent_reg.async_get("sensor.elementary_school_lunch_tomorrow")
        assert today_entry is not None
        assert tomorrow_entry is not None
        assert (
            today_entry.unique_id
            == "nutrislice_my-district_elementary-school_lunch_today"
        )
        assert (
            tomorrow_entry.unique_id
            == "nutrislice_my-district_elementary-school_lunch_tomorrow"
        )

        # On 2026-02-15: Today has no menu, Tomorrow (2026-02-16) is Presidents Day
        today_state = hass.states.get("sensor.elementary_school_lunch_today")
        tomorrow_state = hass.states.get("sensor.elementary_school_lunch_tomorrow")

        assert today_state.state == "No menu"
        assert today_state.attributes.get("date") == "2026-02-15"
        assert today_state.attributes.get("is_holiday") is False
        assert today_state.attributes.get("items_by_category") == {}

        assert tomorrow_state.state == "Presidents Day"
        assert tomorrow_state.attributes.get("date") == "2026-02-16"
        assert tomorrow_state.attributes.get("is_holiday") is True
        assert tomorrow_state.attributes.get("holiday_name") == "Presidents Day"

        # Move to Monday 2026-02-16 (Holiday): Today is Presidents Day, Tomorrow (2026-02-17) has Pizza, Burger
        freezer.move_to("2026-02-16 10:00:00")
        await async_update_entity(hass, "sensor.elementary_school_lunch_today")
        await async_update_entity(hass, "sensor.elementary_school_lunch_tomorrow")

        today_state = hass.states.get("sensor.elementary_school_lunch_today")
        tomorrow_state = hass.states.get("sensor.elementary_school_lunch_tomorrow")

        assert today_state.state == "Presidents Day"
        assert tomorrow_state.state == "Pizza, Burger"
        assert tomorrow_state.attributes.get("date") == "2026-02-17"
        assert tomorrow_state.attributes.get("menu_summary") == "Pizza, Burger, Apple"
        assert tomorrow_state.attributes.get("items_by_category") == {
            "entree": ["Pizza", "Burger"],
            "fruit": ["Apple"],
        }

        # Move to Tuesday 2026-02-17: Today has Pizza, Burger; Tomorrow has No menu
        freezer.move_to("2026-02-17 10:00:00")
        await async_update_entity(hass, "sensor.elementary_school_lunch_today")
        await async_update_entity(hass, "sensor.elementary_school_lunch_tomorrow")

        today_state = hass.states.get("sensor.elementary_school_lunch_today")
        tomorrow_state = hass.states.get("sensor.elementary_school_lunch_tomorrow")

        assert today_state.state == "Pizza, Burger"
        assert today_state.attributes.get("items_by_category") == {
            "entree": ["Pizza", "Burger"],
            "fruit": ["Apple"],
        }
        assert tomorrow_state.state == "No menu"

        # Ensure serialized attributes are tiny (< 1 KB, nowhere near HA's 16 KB limit)
        assert len(json.dumps(dict(today_state.attributes))) < 1024
