"""Sensor platform for the SolarWinds Observability (SWIS) integration.

Each SolarWinds node becomes a Home Assistant device, with CPU, memory and
per-volume sensors, plus a status sensor. The device's `configuration_url`
points at the node's page in the SolarWinds Web Console.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SwisConfigEntry
from .const import DOMAIN, MANUFACTURER, STATUS_NAMES, STATUS_OK
from .coordinator import SwisDataUpdateCoordinator, SwisNodeData

_LOGGER = logging.getLogger(__name__)

BYTES_PER_GB = 1073741824


def _node_device_info(node: SwisNodeData, web_console_url: str) -> DeviceInfo:
    raw = node.raw
    details_url = raw.get("DetailsUrl") or ""
    configuration_url = f"{web_console_url}{details_url}" if details_url else web_console_url

    return DeviceInfo(
        identifiers={(DOMAIN, f"node_{node.node_id}")},
        name=raw.get("Caption") or f"Node {node.node_id}",
        manufacturer=raw.get("Vendor") or MANUFACTURER,
        model=raw.get("MachineType") or None,
        configuration_url=configuration_url,
    )


class SwisNodeEntity(CoordinatorEntity[SwisDataUpdateCoordinator], SensorEntity):
    """Base entity for a sensor tied to one SolarWinds node."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SwisDataUpdateCoordinator,
        node_id: int,
        web_console_url: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._node_id = node_id
        self._web_console_url = web_console_url
        self._attr_unique_id = f"{DOMAIN}_{node_id}_{description.key}"

    @property
    def _node(self) -> SwisNodeData | None:
        return self.coordinator.data.get(self._node_id) if self.coordinator.data else None

    @property
    def available(self) -> bool:
        return super().available and self._node is not None

    @property
    def device_info(self) -> DeviceInfo | None:
        node = self._node
        if node is None:
            return None
        return _node_device_info(node, self._web_console_url)


class SwisNodeStatusSensor(SwisNodeEntity):
    """The node's overall status (Up/Down/Warning/...)."""

    entity_description = SensorEntityDescription(
        key="status",
        translation_key="node_status",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(STATUS_NAMES.values())),
    )

    @property
    def native_value(self) -> str | None:
        node = self._node
        if node is None:
            return None
        status = node.raw.get("Status")
        return STATUS_NAMES.get(status, f"Unknown ({status})")

    @property
    def icon(self) -> str:
        node = self._node
        status = node.raw.get("Status") if node else None
        return "mdi:server-network" if status in STATUS_OK else "mdi:server-network-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        node = self._node
        if node is None:
            return {}
        raw = node.raw
        return {
            "ip_address": raw.get("IPAddress"),
            "dns": raw.get("DNS"),
            "vendor": raw.get("Vendor"),
            "machine_type": raw.get("MachineType"),
            "location": raw.get("Location"),
            "contact": raw.get("Contact"),
            "unmanaged": raw.get("UnManaged"),
            "last_boot": raw.get("LastBoot"),
            "percent_packet_loss": raw.get("PercentLoss"),
        }


class SwisNodeCpuSensor(SwisNodeEntity):
    """Current CPU load, percent."""

    entity_description = SensorEntityDescription(
        key="cpu_load",
        translation_key="cpu_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chip",
    )

    @property
    def native_value(self) -> float | None:
        node = self._node
        return node.raw.get("CPULoad") if node else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        node = self._node
        if node is None:
            return {}
        return {"cpu_count": node.raw.get("CPUCount")}


class SwisNodeMemorySensor(SwisNodeEntity):
    """Current memory utilisation, percent."""

    entity_description = SensorEntityDescription(
        key="percent_memory_used",
        translation_key="percent_memory_used",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    )

    @property
    def native_value(self) -> float | None:
        node = self._node
        return node.raw.get("PercentMemoryUsed") if node else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        node = self._node
        if node is None:
            return {}
        total = node.raw.get("TotalMemory")
        return {"total_memory_gb": round(total / BYTES_PER_GB, 2) if total else None}


class SwisNodeResponseTimeSensor(SwisNodeEntity):
    """ICMP response time, milliseconds."""

    entity_description = SensorEntityDescription(
        key="response_time",
        translation_key="response_time",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    )

    @property
    def native_value(self) -> float | None:
        node = self._node
        return node.raw.get("ResponseTime") if node else None


NODE_SENSOR_CLASSES: tuple[type[SwisNodeEntity], ...] = (
    SwisNodeStatusSensor,
    SwisNodeCpuSensor,
    SwisNodeMemorySensor,
    SwisNodeResponseTimeSensor,
)


class SwisVolumeSensor(CoordinatorEntity[SwisDataUpdateCoordinator], SensorEntity):
    """Percent-used sensor for a single drive/volume on a node."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SwisDataUpdateCoordinator,
        node_id: int,
        volume_id: int,
        volume_name: str,
        web_console_url: str,
    ) -> None:
        super().__init__(coordinator)
        self._node_id = node_id
        self._volume_id = volume_id
        self._web_console_url = web_console_url
        self._attr_unique_id = f"{DOMAIN}_{node_id}_volume_{volume_id}"
        self._attr_translation_key = "volume_percent_used"
        self._attr_translation_placeholders = {"volume": volume_name}
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:harddisk"

    @property
    def _node(self) -> SwisNodeData | None:
        return self.coordinator.data.get(self._node_id) if self.coordinator.data else None

    @property
    def _volume(self) -> dict[str, Any] | None:
        node = self._node
        return node.volumes.get(self._volume_id) if node else None

    @property
    def available(self) -> bool:
        return super().available and self._volume is not None

    @property
    def name(self) -> str:
        volume = self._volume
        caption = volume.get("Caption") if volume else None
        return caption or f"Volume {self._volume_id}"

    @property
    def native_value(self) -> float | None:
        volume = self._volume
        return volume.get("VolumePercentUsed") if volume else None

    @property
    def device_info(self) -> DeviceInfo | None:
        node = self._node
        if node is None:
            return None
        return _node_device_info(node, self._web_console_url)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        volume = self._volume
        if volume is None:
            return {}
        size = volume.get("VolumeSize")
        used = volume.get("VolumeSpaceUsed")
        free = volume.get("VolumeSpaceAvailable")
        return {
            "volume_type": volume.get("VolumeType"),
            "size_gb": round(size / BYTES_PER_GB, 2) if size else None,
            "used_gb": round(used / BYTES_PER_GB, 2) if used else None,
            "free_gb": round(free / BYTES_PER_GB, 2) if free else None,
            "responding": volume.get("VolumeResponding"),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SwisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SWIS sensors from a config entry, and keep adding new ones as they appear."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    web_console_url = runtime.web_console_url

    known_nodes: set[int] = set()
    known_volumes: set[int] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[SensorEntity] = []
        data = coordinator.data or {}

        for node_id, node in data.items():
            if node_id not in known_nodes:
                known_nodes.add(node_id)
                new_entities.extend(
                    cls(coordinator, node_id, web_console_url, cls.entity_description)
                    for cls in NODE_SENSOR_CLASSES
                )
            for volume_id, volume in node.volumes.items():
                if volume_id not in known_volumes:
                    known_volumes.add(volume_id)
                    new_entities.append(
                        SwisVolumeSensor(
                            coordinator,
                            node_id,
                            volume_id,
                            volume.get("Caption") or f"Volume {volume_id}",
                            web_console_url,
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
