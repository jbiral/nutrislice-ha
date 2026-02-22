"""Test the Nutrislice sensor."""
import pytest
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.nutrislice.const import DOMAIN
from custom_components.nutrislice.sensor import NutrisliceSensor
from custom_components.nutrislice.coordinator import NutrisliceDataUpdateCoordinator


@pytest.mark.asyncio
async def test_sensor_state_and_attributes(hass: HomeAssistant) -> None:
    """Test the sensor parses data correctly."""
    coordinator = NutrisliceDataUpdateCoordinator(
        hass, district="my-district", school_name="elementary-school", meal_type="lunch"
    )

    # Mock data directly
    mock_data = {
        "current_week": {
            "days": [
                {
                    "date": "2026-02-16",
                    "menu_items": [
                        {
                            "is_holiday": True,
                            "text": "Presidents Day",
                        }
                    ]
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
                                "food_category": "sides",
                                "name": "Apple",
                            },
                        }
                    ]
                }
            ]
        },
        "next_week": None
    }
    
    coordinator.data = mock_data
    from unittest.mock import MagicMock
    mock_entry = MagicMock()
    mock_entry.data = {
        "district": "my-district",
        "school_name": "elementary-school",
        "meal_type": "lunch",
        "categories": ["entree", "sides"]
    }
    
    sensor = NutrisliceSensor(coordinator, mock_entry)
    
    # 1. Test basic attributes (name/id)
    assert sensor.name == "Elementary School Lunch"
    assert sensor.unique_id == "nutrislice_my-district_elementary-school_lunch"

    # 2. Test attributes parsing
    attrs = sensor.extra_state_attributes
    assert attrs["district"] == "my-district"
    assert len(attrs["days"]) == 2
    
    # Check Holiday Day
    holiday_day = attrs["days"][0]
    assert holiday_day["date"] == "2026-02-16"
    assert holiday_day["is_holiday"] is True
    assert holiday_day["holiday_name"] == "Presidents Day"
    
    # Check Regular Menu Day
    menu_day = attrs["days"][1]
    assert menu_day["date"] == "2026-02-17"
    assert menu_day["is_holiday"] is False
    assert menu_day["has_menu"] is True
    assert len(menu_day["menu_items"]) == 3
    assert menu_day["menu_items"][0]["name"] == "Pizza"
    assert menu_day["menu_items"][0]["category"] == "entree"

    # 3. Test State (Depends on today's date, mock datetime)
    with patch("custom_components.nutrislice.sensor.datetime") as mock_datetime:
        # Mock today as the holiday
        mock_now = mock_datetime.now.return_value
        mock_now.strftime.return_value = "2026-02-16"
        mock_now.hour = 10
        assert sensor.native_value == "Presidents Day"
        
        # Mock today as the menu day
        mock_now.strftime.return_value = "2026-02-17"
        mock_now.hour = 10
        assert sensor.native_value == "2 Entrees Available"
    
    # 4. Test set_target_date service (Handle the timedelta logic)
    with patch("custom_components.nutrislice.sensor.datetime") as mock_datetime:
        from datetime import datetime as dt
        mock_now = mock_datetime.now.return_value
        mock_now.strftime.side_effect = lambda fmt: (dt(2026, 2, 17) if fmt == "%Y-%m-%d" else dt(2026, 2, 17)).strftime(fmt)
        mock_now.hour = 10 # Before 1 PM - THIS WAS TRIGGERING THE ERROR
        
        # This SHOULD NO LONGER fail with UnboundLocalError
        attrs = sensor.extra_state_attributes
        assert attrs["target_date"] == "2026-02-17"
