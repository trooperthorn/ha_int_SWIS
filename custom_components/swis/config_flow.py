"""Config flow for the SolarWinds Observability (SWIS) integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import SwisAuthError, SwisClient, SwisConnectionError, SwisError
from .const import (
    CONF_VERIFY_SSL,
    CONF_VOLUME_TYPES,
    CONF_WEB_CONSOLE_URL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_VOLUME_TYPES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CAPABILITY_QUERY = "SELECT TOP 1 n.NodeID FROM Orion.Nodes n"

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_USERNAME): TextSelector(),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): BooleanSelector(),
        vol.Optional(CONF_WEB_CONSOLE_URL): TextSelector(),
    }
)


async def _validate(hass: Any, data: dict[str, Any]) -> None:
    """Raise SwisError/SwisAuthError/SwisConnectionError on failure."""
    session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])
    client = SwisClient(
        session,
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        port=int(data[CONF_PORT]),
        verify_ssl=data[CONF_VERIFY_SSL],
    )
    await client.query(CAPABILITY_QUERY)


class SwisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolarWinds Observability (SWIS)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Left blank, this means "auto-detect from Orion.Websites" (see
            # coordinator.py); only store a value here if the user overrode it.
            web_console_url = (user_input.get(CONF_WEB_CONSOLE_URL) or "").rstrip("/")

            data = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: int(user_input[CONF_PORT]),
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                CONF_WEB_CONSOLE_URL: web_console_url,
            }

            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}")
            self._abort_if_unique_id_configured()

            try:
                await _validate(self.hass, data)
            except SwisAuthError:
                errors["base"] = "invalid_auth"
            except SwisConnectionError:
                errors["base"] = "cannot_connect"
            except SwisError:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=data[CONF_HOST], data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SwisOptionsFlow()


class SwisOptionsFlow(OptionsFlowWithReload):
    """Options: polling interval and which volume types to expose as sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(min=30, max=3600, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_VOLUME_TYPES,
                    default=options.get(CONF_VOLUME_TYPES, DEFAULT_VOLUME_TYPES),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            "Fixed Disk",
                            "Network Disk",
                            "Virtual Memory",
                            "RAM Disk",
                            "Compact Disk",
                            "Removable Disk",
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=True,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
