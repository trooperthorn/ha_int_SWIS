"""Constants for the SolarWinds Observability (SWIS) integration."""
from __future__ import annotations

DOMAIN = "swis"

CONF_VERIFY_SSL = "verify_ssl"
CONF_WEB_CONSOLE_URL = "web_console_url"
CONF_VOLUME_TYPES = "volume_types"

DEFAULT_PORT = 17774
DEFAULT_VERIFY_SSL = True
DEFAULT_SCAN_INTERVAL = 300
DEFAULT_TIMEOUT = 30
DEFAULT_VOLUME_TYPES = ["Fixed Disk"]

MANUFACTURER = "SolarWinds"

# Orion.Nodes.Status values that count as unmanaged/no data, mirrored from
# Orion.StatusInfo (see docs/reference/status-codes.md in the SolarWinds_OrionGuides repo).
STATUS_NAMES: dict[int, str] = {
    0: "Unknown",
    1: "Up",
    2: "Down",
    3: "Warning",
    4: "Shutdown",
    5: "Testing",
    6: "Dormant",
    7: "Not Present",
    8: "Lower Layer Down",
    9: "Unmanaged",
    10: "Unplugged",
    11: "External",
    12: "Unreachable",
    14: "Critical",
    15: "Partly Available",
    16: "Misconfigured",
    17: "Could Not Poll",
    19: "Unconfirmed",
    22: "Active",
    24: "Inactive",
    25: "Expired",
    26: "Monitoring Disabled",
    27: "Disabled",
    28: "Not Licensed",
    29: "Other Category",
    30: "Not Running",
}

# Statuses that are considered "OK"/up for a binary problem indicator.
STATUS_OK = {1, 5, 6, 22}
