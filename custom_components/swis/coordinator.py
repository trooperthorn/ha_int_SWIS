"""DataUpdateCoordinator for the SWIS integration."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SwisAuthError, SwisClient, SwisConnectionError, SwisError

_LOGGER = logging.getLogger(__name__)

NODES_QUERY = """
SELECT
    n.NodeID, n.Caption, n.IPAddress, n.DNS, n.SysName, n.Vendor, n.MachineType,
    n.Location, n.Contact, n.Status, n.UnManaged,
    n.CPULoad, n.CPUCount, n.PercentMemoryUsed, n.TotalMemory,
    n.ResponseTime, n.PercentLoss, n.LastBoot, n.SystemUpTime,
    n.DetailsUrl, n.Uri
FROM Orion.Nodes n
ORDER BY n.NodeID
"""

VOLUMES_QUERY = """
SELECT
    v.VolumeID, v.NodeID, v.Caption, v.VolumeType, v.VolumeDescription,
    v.VolumePercentUsed, v.VolumeSize, v.VolumeSpaceUsed, v.VolumeSpaceAvailable,
    v.VolumeResponding, v.Status, v.UnManaged
FROM Orion.Volumes v
WHERE v.VolumeType IN @volumeTypes
ORDER BY v.NodeID, v.Caption
"""

_MAC_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")

# Orion.Nodes carries no MAC address of its own; it lives per-interface on
# Orion.NPM.Interfaces, which requires the NPM module to be licensed. Queried
# separately and best-effort, so a server without NPM simply reports no MACs.
INTERFACES_MAC_QUERY = """
SELECT i.NodeID, i.InterfaceID, i.PhysicalAddress
FROM Orion.NPM.Interfaces i
WHERE i.PhysicalAddress IS NOT NULL AND i.PhysicalAddress <> ''
ORDER BY i.NodeID, i.InterfaceID
"""


@dataclass
class SwisNodeData:
    """One monitored node, plus the volumes attached to it."""

    node_id: int
    raw: dict[str, Any]
    volumes: dict[int, dict[str, Any]] = field(default_factory=dict)
    mac_address: str | None = None


class SwisDataUpdateCoordinator(DataUpdateCoordinator[dict[int, SwisNodeData]]):
    """Poll SWIS for nodes and their volumes on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SwisClient,
        volume_types: list[str],
        update_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{entry.title} (SWIS)",
            update_interval=timedelta(seconds=update_interval),
        )
        self._client = client
        self._volume_types = volume_types
        # None = not probed yet, True/False = whether Orion.NPM.Interfaces answered.
        self._npm_interfaces_available: bool | None = None

    async def _async_update_data(self) -> dict[int, SwisNodeData]:
        try:
            nodes = await self._client.query(NODES_QUERY)
            volumes = await self._client.query(
                VOLUMES_QUERY, volumeTypes=self._volume_types
            )
        except SwisAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SwisConnectionError as err:
            raise UpdateFailed(f"Could not reach SolarWinds: {err}") from err
        except SwisError as err:
            raise UpdateFailed(f"Error querying SolarWinds: {err}") from err

        result: dict[int, SwisNodeData] = {
            row["NodeID"]: SwisNodeData(node_id=row["NodeID"], raw=row) for row in nodes
        }
        for vol in volumes:
            node = result.get(vol["NodeID"])
            if node is not None:
                node.volumes[vol["VolumeID"]] = vol

        try:
            macs = await self._async_get_macs()
        except SwisAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SwisConnectionError as err:
            raise UpdateFailed(f"Could not reach SolarWinds: {err}") from err

        for node_id, mac in macs.items():
            node = result.get(node_id)
            if node is not None:
                node.mac_address = mac

        return result

    async def _async_get_macs(self) -> dict[int, str]:
        """Return the first known MAC per node, from Orion.NPM.Interfaces.

        NPM is a separately licensed module: a server without it answers this
        query with an error rather than an empty result. That is treated as
        "no MACs available" rather than a failed update, and is only logged
        once so it does not spam every poll.
        """
        if self._npm_interfaces_available is False:
            return {}

        try:
            interfaces = await self._client.query(INTERFACES_MAC_QUERY)
        except (SwisAuthError, SwisConnectionError):
            # A real connectivity/credentials problem, not "NPM isn't licensed".
            # Let it surface the same way the nodes/volumes queries do.
            raise
        except SwisError as err:
            if self._npm_interfaces_available is not False:
                _LOGGER.info(
                    "Orion.NPM.Interfaces is not available (%s); "
                    "MAC addresses will not be reported for devices",
                    err,
                )
            self._npm_interfaces_available = False
            return {}

        self._npm_interfaces_available = True

        macs: dict[int, str] = {}
        for row in interfaces:
            node_id = row["NodeID"]
            if node_id in macs:
                continue
            mac = format_mac(row["PhysicalAddress"])
            if _MAC_RE.match(mac):
                macs[node_id] = mac
        return macs
