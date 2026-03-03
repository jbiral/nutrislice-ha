"""Test the Nutrislice coordinator."""

from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.nutrislice.coordinator import NutrisliceDataUpdateCoordinator
from custom_components.nutrislice.model import NutrisliceConfig
import aiohttp


@pytest.fixture
def coordinator(hass: HomeAssistant):
    """Fixture to provide a NutrisliceDataUpdateCoordinator."""
    config = NutrisliceConfig(
        district="test_district",
        school_name="test_school",
        meal_type="test_meal",
        categories=["test_category"],
    )
    return NutrisliceDataUpdateCoordinator(hass, config)


@pytest.mark.asyncio
async def test_coordinator_parallel_fetch(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
):
    """Test that the coordinator fetches the 3 weeks concurrently and correctly."""

    mock_session = MagicMock()

    # We will simulate successful API responses, ensuring all 3 resolve
    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        # Return empty days array to satisfy the basic Pydantic model
        mock_resp.json.return_value = {"days": []}

        # We need to return an object that acts as an async context manager
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


@pytest.mark.asyncio
async def test_coordinator_current_week_failure_raises(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
):
    """Test that failure to fetch the current week raises UpdateFailed."""

    mock_session = MagicMock()

    # We will simulate failure for the current week specifically
    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()

        # The URL ends with today's date vs previous/next week
        # We can just fail them all or fail the one that is current week.
        # Let's say all return 500 for simplicity.
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


@pytest.mark.asyncio
async def test_coordinator_other_weeks_failure_degrades_gracefully(
    hass: HomeAssistant, coordinator: NutrisliceDataUpdateCoordinator
):
    """Test that failure on previous/next weeks does not block the update completely."""

    mock_session = MagicMock()

    def mock_get(url, *args, **kwargs):
        mock_resp = AsyncMock()

        from datetime import datetime

        today_str = datetime.now().strftime("%Y/%m/%d")

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

        # Current week should have data (empty object since we returned empty days)
        assert result["current_week"] is not None
        # Previous/next week should gracefully fall back to None
        assert result["previous_week"] is None
        assert result["next_week"] is None
