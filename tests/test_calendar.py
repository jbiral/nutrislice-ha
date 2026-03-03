"""Test the Nutrislice calendar."""

from unittest.mock import patch, AsyncMock
from datetime import datetime

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nutrislice.const import DOMAIN


async def test_calendar_creation_and_events(
    hass: HomeAssistant, freezer, mock_nutrislice_data_validated
):
    """Test the calendar platform parses data correctly."""

    # Provide data where 2026-02-16 is a holiday and 2026-02-17 has a menu
    freezer.move_to("2026-02-15")

    with patch(
        "custom_components.nutrislice.coordinator.NutrisliceDataUpdateCoordinator._async_update_data",
        new_callable=AsyncMock,
        return_value=mock_nutrislice_data_validated,
    ):
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "district": "my-district",
                "school_name": "elementary-school",
                "meal_type": "lunch",
                "categories": ["entree", "fruit"],
            },
            entry_id="test_calendar_id",
        )
        mock_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()

        # Verify the calendar entity was created
        state = hass.states.get("calendar.elementary_school_lunch")
        assert state is not None
        assert state.attributes.get("friendly_name") == "Elementary School Lunch"

        # Check `event` property calculation for the "next" event.
        # Since today is 2026-02-15 (Sunday) and menu starts on 16th (holiday),
        # the next event should be the holiday on the 16th.
        assert state.state != "unknown"
        assert state.attributes.get("message") == "Holiday: Presidents Day"

        # Test fetching events via the `get_events` service
        # (directly calling the method for unit test simplicity)
        calendar = hass.data["entity_components"]["calendar"].get_entity(
            "calendar.elementary_school_lunch"
        )

        start_dt = datetime(2026, 2, 1, 0, 0, 0)
        end_dt = datetime(2026, 2, 28, 23, 59, 59)
        events = await calendar.async_get_events(hass, start_dt, end_dt)

        assert len(events) >= 2

        holiday_event = next(e for e in events if e.start.isoformat() == "2026-02-16")
        assert holiday_event.summary == "Holiday: Presidents Day"
        assert holiday_event.description == "No school meal service."

        menu_event = next(e for e in events if e.start.isoformat() == "2026-02-17")
        assert menu_event.summary == "Menu: 3 items"
        assert "Entree: Pizza, Burger" in menu_event.description
        assert "Fruit: Apple" in menu_event.description
