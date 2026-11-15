"""Test the Nutrislice coordinator and Pydantic models."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.nutrislice.coordinator import NutrisliceDataUpdateCoordinator
from custom_components.nutrislice.model import NutrisliceConfig, NutrisliceResponse


@pytest.fixture
def coordinator(hass: HomeAssistant) -> NutrisliceDataUpdateCoordinator:
    """Fixture to provide a NutrisliceDataUpdateCoordinator."""
    config = NutrisliceConfig(
        district="test_district",
        school_name="test_school",
        meal_type="test_meal",
        categories=["test_category"],
    )
    return NutrisliceDataUpdateCoordinator(hass, config)


async def test_coordinator_parallel_fetch(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
) -> None:
    """Test that the coordinator fetches the 3 weeks concurrently and correctly."""
    mock_session = MagicMock()

    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"days": []}

        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        return cm

    mock_session.get = MagicMock(side_effect=mock_get)

    with patch(
        "custom_components.nutrislice.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        result = await coordinator._async_update_data()

        assert "current_week" in result
        assert "previous_week" in result
        assert "next_week" in result
        assert result["current_week"] is not None
        assert mock_session.get.call_count == 3


async def test_coordinator_current_week_failure_raises(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
) -> None:
    """Test that failure to fetch the current week raises UpdateFailed."""
    mock_session = MagicMock()

    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        mock_resp.status = 500

        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        return cm

    mock_session.get = mock_get

    with patch(
        "custom_components.nutrislice.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        with pytest.raises(UpdateFailed) as exc:
            await coordinator._async_update_data()
        assert "Error fetching current week" in str(exc.value)


async def test_coordinator_other_weeks_failure_degrades_gracefully(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
) -> None:
    """Test that failure on previous/next weeks does not block the update completely."""
    mock_session = MagicMock()

    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        today_str = dt_util.now().date().strftime("%Y/%m/%d")

        if today_str in url:
            mock_resp.status = 200
            mock_resp.json.return_value = {"days": []}
        else:
            mock_resp.status = 500

        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        return cm

    mock_session.get = mock_get

    with patch(
        "custom_components.nutrislice.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        result = await coordinator._async_update_data()

        assert result["current_week"] is not None
        assert result["previous_week"] is None
        assert result["next_week"] is None


async def test_coordinator_filters_categories_and_handles_aliases_and_unknowns(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
) -> None:
    """Test category filtering, fallback to food_category, aliases, and unknown categories."""
    coordinator.config.categories = ["entree", "sides"]

    raw_json = {
        "days": [
            {
                "date": "2026-03-02",
                "menu_items": [
                    {
                        "is_holiday": False,
                        "text": "Pizza",
                        "category": "entree",
                        "food": {
                            "name": "Pizza",
                            "food_category": "entree",
                        },
                    },
                    {
                        # Empty item.category, populated food.food_category + alias ("side" -> "sides")
                        "is_holiday": False,
                        "text": "",
                        "category": "",
                        "food": {
                            "name": "Garlic Bread",
                            "food_category": "side",
                        },
                    },
                    {
                        # Unknown category ("chef_special") should not crash Pydantic validation
                        "is_holiday": False,
                        "text": "Mystery Dish",
                        "category": "chef_special",
                        "food": {
                            "name": "Mystery Dish",
                            "food_category": "chef_special",
                        },
                    },
                    {
                        "is_holiday": False,
                        "text": "Apple",
                        "category": "fruit",
                        "food": {
                            "name": "Apple",
                            "food_category": "fruit",
                        },
                    },
                    {
                        # Empty item.category AND empty food_category on a real food (e.g. Macaroni and Cheese)
                        # Plus comma-separated string ID as returned by live Nutrislice endpoints
                        "id": "438056538,438056540,2992243",
                        "is_holiday": False,
                        "text": "",
                        "category": "",
                        "food": {
                            "id": "5001,5002",
                            "name": "Macaroni and Cheese",
                            "food_category": "",
                        },
                    },
                    {
                        "is_holiday": True,
                        "text": "School Closure",
                        "category": None,
                    },
                ],
            }
        ]
    }

    mock_session = MagicMock()

    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = raw_json
        cm = AsyncMock()
        cm.__aenter__.return_value = mock_resp
        return cm

    mock_session.get = mock_get

    with patch(
        "custom_components.nutrislice.coordinator.async_get_clientsession",
        return_value=mock_session,
    ):
        result = await coordinator._async_update_data()

    day = result["current_week"].days[0]
    items = day.menu_items

    # Pizza (entree), Garlic Bread (side -> sides), Macaroni and Cheese ("" -> entree), and School Closure (holiday) remain
    assert len(items) == 4
    assert items[0].food.name == "Pizza"
    assert items[1].food.name == "Garlic Bread"
    assert items[1].effective_category == "side"
    assert items[2].food.name == "Macaroni and Cheese"
    assert items[2].effective_category == "entree"
    assert items[3].text == "School Closure"


async def test_coordinator_deduplicates_and_sorts_days(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
) -> None:
    """Test get_all_days deduplicates overlapping dates and sorts chronologically."""
    coordinator.data = {
        "next_week": NutrisliceResponse.model_validate(
            {
                "days": [
                    {"date": "2026-03-09", "menu_items": []},
                ]
            }
        ),
        "previous_week": NutrisliceResponse.model_validate(
            {
                "days": [
                    {"date": "2026-02-23", "menu_items": []},
                    # Overlapping date with empty items in previous_week
                    {"date": "2026-03-02", "menu_items": []},
                ]
            }
        ),
        "current_week": NutrisliceResponse.model_validate(
            {
                "days": [
                    {
                        "date": "2026-03-02",
                        "menu_items": [
                            {
                                "is_holiday": True,
                                "text": "Staff Development Day",
                                "category": "",
                            }
                        ],
                    }
                ]
            }
        ),
    }

    all_days = coordinator.get_all_days()
    assert [d.date for d in all_days] == [
        date(2026, 2, 23),
        date(2026, 3, 2),
        date(2026, 3, 9),
    ]
    # Overlapping date should keep the populated day from current_week
    march_2 = coordinator.get_day(date(2026, 3, 2))
    assert march_2 is not None
    assert march_2.holiday_name == "Staff Development Day"
