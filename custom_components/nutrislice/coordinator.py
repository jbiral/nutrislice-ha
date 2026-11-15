"""Data update coordinator for Nutrislice."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SCAN_INTERVAL
from .model import Day, NutrisliceConfig, NutrisliceResponse

_LOGGER = logging.getLogger(__name__)


class NutrisliceDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, NutrisliceResponse | None]]
):
    """Class to manage fetching Nutrislice data from their JSON API.

    This coordinator handles fetching three weeks of data (previous, current, and next)
    and provides deduplicated, chronologically sorted access to daily menus.
    """

    def __init__(self, hass: HomeAssistant, config: NutrisliceConfig) -> None:
        """Initialize the coordinator."""
        self.config = config

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    def _filter_categories(self, response: NutrisliceResponse) -> NutrisliceResponse:
        """Filter menu items to only keep holidays and configured categories."""
        return response.filter_categories(self.config.categories)

    def get_all_days(self) -> list[Day]:
        """Return all fetched days, deduplicated and sorted chronologically."""
        if not self.data:
            return []

        unique_days: dict[date, Day] = {}
        for week in self.data.values():
            if week is None:
                continue
            for day in week.days:
                existing = unique_days.get(day.date)
                # Prefer a Day entry that has menu items if weeks overlap
                if existing is None or (not existing.menu_items and day.menu_items):
                    unique_days[day.date] = day

        return [unique_days[d] for d in sorted(unique_days.keys())]

    def get_day(self, target_date: date) -> Day | None:
        """Return the Day model for a specific date, if available."""
        for day in self.get_all_days():
            if day.date == target_date:
                return day
        return None

    async def _fetch_week(
        self, session, key: str, week_date: date | datetime
    ) -> tuple[str, NutrisliceResponse | None]:
        """Fetch and validate a single week's menu from the Nutrislice API."""
        url = (
            f"https://{self.config.district}.api.nutrislice.com/menu/api/weeks/"
            f"school/{self.config.school_name}/menu-type/{self.config.meal_type}/"
            f"{week_date.strftime('%Y/%m/%d')}/?format=json"
        )
        try:
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    if response.status == 200:
                        raw_json = await response.json()
                        validated_response = NutrisliceResponse.model_validate(raw_json)
                        filtered_response = self._filter_categories(validated_response)
                        return key, filtered_response
                    if key == "current_week":
                        raise UpdateFailed(
                            f"Error fetching current week: {response.status}"
                        )
                _LOGGER.debug("Could not fetch %s: %s", key, response.status)
                return key, None
        except UpdateFailed:
            raise
        except Exception as err:
            if key == "current_week":
                raise UpdateFailed(
                    f"Error communicating with API for current week: {err}"
                ) from err
            _LOGGER.debug("Error fetching %s: %s", key, err)
            return key, None

    async def _async_update_data(self) -> dict[str, NutrisliceResponse | None]:
        """Update data via API."""
        session = async_get_clientsession(self.hass)
        today = dt_util.now().date()

        # Calculate the dates for the three-week window
        weeks_to_fetch = {
            "previous_week": today - timedelta(days=7),
            "current_week": today,
            "next_week": today + timedelta(days=7),
        }

        tasks = [
            self._fetch_week(session, key, week_date)
            for key, week_date in weeks_to_fetch.items()
        ]

        try:
            results = await asyncio.gather(*tasks)
            return dict(results)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
