"""Data update coordinator for Nutrislice."""

import logging
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .model import NutrisliceConfig

_LOGGER = logging.getLogger(__name__)


class NutrisliceDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nutrislice data from their JSON API.

    This coordinator handles fetching three weeks of data (previous, current, and next)
    to ensure smooth transitions for the user and to provide enough data for the
    frontend Lovelace card.
    """

    def __init__(self, hass: HomeAssistant, config: NutrisliceConfig) -> None:
        """Initialize."""
        self.config = config

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via API."""
        try:
            # We fetch data for the previous, current, and next week.
            # Nutrislice API takes any date in the week and returns the whole week.
            today = datetime.now()
            prev_week = today - timedelta(days=7)
            next_week = today + timedelta(days=7)

            data = {}

            async with aiohttp.ClientSession() as session:
                # Fetch previous week
                url_prev = f"https://{self.config.district}.api.nutrislice.com/menu/api/weeks/school/{self.config.school_name}/menu-type/{self.config.meal_type}/{prev_week.strftime('%Y/%m/%d')}/?format=json"
                async with session.get(url_prev, timeout=10) as response:
                    if response.status == 200:
                        data["previous_week"] = await response.json()
                    else:
                        data["previous_week"] = None

                # Fetch current week
                url_current = f"https://{self.config.district}.api.nutrislice.com/menu/api/weeks/school/{self.config.school_name}/menu-type/{self.config.meal_type}/{today.strftime('%Y/%m/%d')}/?format=json"
                async with session.get(url_current, timeout=10) as response:
                    if response.status != 200:
                        raise UpdateFailed(
                            f"Error fetching current week: {response.status}"
                        )
                    current_week = await response.json()
                    data["current_week"] = current_week

                # Fetch next week
                url_next = f"https://{self.config.district}.api.nutrislice.com/menu/api/weeks/school/{self.config.school_name}/menu-type/{self.config.meal_type}/{next_week.strftime('%Y/%m/%d')}/?format=json"
                async with session.get(url_next, timeout=10) as response:
                    if response.status == 200:
                        next_week_data = await response.json()
                        data["next_week"] = next_week_data
                    else:
                        # Sometimes next week isn't published yet, we just ignore it
                        data["next_week"] = None

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
