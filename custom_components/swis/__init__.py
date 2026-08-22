"""The SolarWinds Observability (SWIS) integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SwisClient
from .const import (
    CONF_VERIFY_SSL,
    CONF_VOLUME_TYPES,
    CONF_WEB_CONSOLE_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOLUME_TYPES,
)
from .coordinator import SwisDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class SwisRuntimeData:
    """Runtime data stored on the config entry."""

    coordinator: SwisDataUpdateCoordinator
    web_console_url: str


SwisConfigEntry = ConfigEntry[SwisRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SwisConfigEntry) -> bool:
    """Set up SWIS from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data[CONF_VERIFY_SSL])
    client = SwisClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        port=entry.data[CONF_PORT],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
    )

    volume_types = entry.options.get(CONF_VOLUME_TYPES, DEFAULT_VOLUME_TYPES)
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    coordinator = SwisDataUpdateCoordinator(
        hass, entry, client, volume_types, scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SwisRuntimeData(
        coordinator=coordinator,
        web_console_url=entry.data.get(CONF_WEB_CONSOLE_URL)
        or f"https://{entry.data[CONF_HOST]}",
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: SwisConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SwisConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
