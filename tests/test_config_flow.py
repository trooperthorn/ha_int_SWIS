"""Config-flow and options-flow contract tests."""
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swis.api import SwisAuthError, SwisConnectionError, SwisError
from custom_components.swis.const import DOMAIN

pytestmark = pytest.mark.asyncio

USER_INPUT = {
    "host": "orion.example.internal",
    "port": 17774,
    "username": "orion-ro",
    "password": "not-a-real-password",
    "verify_ssl": True,
}


async def _start_and_submit(hass, side_effect=None):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["step_id"] == "user"
    with patch(
        "custom_components.swis.config_flow._validate", side_effect=side_effect
    ):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )


async def test_user_flow_creates_entry(hass):
    result = await _start_and_submit(hass)

    assert result["type"] == "create_entry"
    assert result["title"] == USER_INPUT["host"]
    assert result["data"]["host"] == USER_INPUT["host"]
    assert result["data"]["port"] == USER_INPUT["port"]


async def test_user_flow_aborts_on_duplicate(hass):
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{USER_INPUT['host']}:{USER_INPUT['port']}",
        data=USER_INPUT,
    ).add_to_hass(hass)

    result = await _start_and_submit(hass)

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SwisAuthError("bad credentials"), "invalid_auth"),
        (SwisConnectionError("unreachable"), "cannot_connect"),
        (SwisError("weird response"), "unknown"),
    ],
)
async def test_user_flow_reports_validation_errors(hass, error, expected):
    result = await _start_and_submit(hass, side_effect=error)

    assert result["type"] == "form"
    assert result["errors"] == {"base": expected}


async def test_options_flow_updates_without_a_config_entry_listener(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{USER_INPUT['host']}:{USER_INPUT['port']}",
        data=USER_INPUT,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 300, "volume_types": ["Fixed Disk"]}
    )
    assert result["type"] == "create_entry"
    assert entry.options["scan_interval"] == 300
