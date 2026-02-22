"""Test the Nutrislice config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.nutrislice.const import (
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.nutrislice.config_flow.aiohttp.ClientSession.get"
        ) as mock_get,
        patch(
            "custom_components.nutrislice.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        # Mock successful API response
        mock_response = mock_get.return_value.__aenter__.return_value
        mock_response.status = 200
        mock_response.json.return_value = {"days": [{"date": "2023-01-01"}]}

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_DISTRICT: "my-district",
                CONF_SCHOOL_NAME: "elementary-school",
                CONF_MEAL_TYPE: "lunch",
            },
        )
        await hass.async_block_till_done()

        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "categories"

        # Step 2: Categories selection
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "categories": ["entree", "sides"],
            },
        )
        await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Nutrislice: Elementary School - Lunch"
    assert result3["data"] == {
        CONF_DISTRICT: "my-district",
        CONF_SCHOOL_NAME: "elementary-school",
        CONF_MEAL_TYPE: "lunch",
        "categories": ["entree", "sides"],
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.nutrislice.config_flow.aiohttp.ClientSession.get"
    ) as mock_get:
        # Mock failed API response
        mock_response = mock_get.return_value.__aenter__.return_value
        mock_response.status = 404

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_DISTRICT: "bad_district",
                CONF_SCHOOL_NAME: "bad_school",
                CONF_MEAL_TYPE: "lunch",
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.nutrislice.config_flow.aiohttp.ClientSession.get",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_DISTRICT: "unionsd",
                CONF_SCHOOL_NAME: "lietz-elementary",
                CONF_MEAL_TYPE: "lunch",
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
