"""Test the Nutrislice config flow and options flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nutrislice.const import (
    CONF_CATEGORIES,
    CONF_DISTRICT,
    CONF_MEAL_TYPE,
    CONF_SCHOOL_NAME,
    DOMAIN,
)


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form and can complete the 2-step setup."""
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
        mock_response = mock_get.return_value.__aenter__.return_value
        mock_response.status = 200
        mock_response.json.return_value = {
            "days": [{"date": "2026-02-17", "menu_items": []}]
        }

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

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_CATEGORIES: ["entree", "sides"],
            },
        )
        await hass.async_block_till_done()

    assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Nutrislice: Elementary School - Lunch"
    assert result3["data"] == {
        CONF_DISTRICT: "my-district",
        CONF_SCHOOL_NAME: "elementary-school",
        CONF_MEAL_TYPE: "lunch",
        CONF_CATEGORIES: ["entree", "sides"],
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.nutrislice.config_flow.aiohttp.ClientSession.get"
    ) as mock_get:
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
                CONF_DISTRICT: "some-district",
                CONF_SCHOOL_NAME: "some-school",
                CONF_MEAL_TYPE: "lunch",
            },
        )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test reconfiguring categories via the OptionsFlow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DISTRICT: "my-district",
            CONF_SCHOOL_NAME: "elementary-school",
            CONF_MEAL_TYPE: "lunch",
            CONF_CATEGORIES: ["entree"],
        },
        entry_id="test_options_id",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CATEGORIES: ["entree", "fruit", "milk"]},
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_CATEGORIES: ["entree", "fruit", "milk"]}
