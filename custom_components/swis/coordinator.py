"""DataUpdateCoordinator for the SWIS integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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


@dataclass
class SwisNodeData:
    """One monitored node, plus the volumes attached to it."""

    node_id: int
    raw: dict[str, Any]
    volumes: dict[int, dict[str, Any]] = field(default_factory=dict)


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

        return result
