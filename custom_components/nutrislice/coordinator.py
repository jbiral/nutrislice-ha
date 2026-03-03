"""Data update coordinator for Nutrislice."""

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .model import NutrisliceConfig, NutrisliceResponse

_LOGGER = logging.getLogger(__name__)


class NutrisliceDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, NutrisliceResponse | None]]
):
    """Class to manage fetching Nutrislice data from their JSON API.

    This coordinator handles fetching three weeks of data (previous, current, and next)
    to ensure smooth transitions for the user.
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

    async def _fetch_week(
        self, session, key: str, week_date: datetime
    ) -> tuple[str, NutrisliceResponse | None]:
        url = (
            f"https://{self.config.district}.api.nutrislice.com/menu/api/weeks/"
            f"school/{self.config.school_name}/menu-type/{self.config.meal_type}/"
            f"{week_date.strftime('%Y/%m/%d')}/?format=json"
        )
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    raw_json = await response.json()
                    return key, NutrisliceResponse.model_validate(raw_json)
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
        today = datetime.now()

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
