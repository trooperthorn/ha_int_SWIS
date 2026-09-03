"""Setup and unload contract tests for the SWIS integration."""
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swis.const import DOMAIN

pytestmark = pytest.mark.asyncio

ENTRY_DATA = {
    "host": "orion.example.internal",
    "port": 17774,
    "username": "orion-ro",
    "password": "not-a-real-password",
    "verify_ssl": True,
    "web_console_url": "",
}


async def test_setup_and_unload_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.swis.api.SwisClient.query", AsyncMock(return_value=[])
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state.value == "loaded"
        assert entry.runtime_data.coordinator is not None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state.value == "not_loaded"
