# SolarWinds Observability (SWIS) for Home Assistant

A Home Assistant custom integration for **SolarWinds Observability Self-Hosted**
(the Orion Platform). It connects to the SolarWinds Information Service (SWIS)
REST API and exposes each monitored **Node** as a Home Assistant device, with
sensors for CPU load, memory usage, and per-volume ("drive") disk usage.

Each device links back to the node's page in the SolarWinds Web Console.

## Features

- **Devices**: one Home Assistant device per SolarWinds node (`Orion.Nodes`).
- **Sensors** per node:
  - **State** — Up / Down / Warning / etc. (from `Orion.Nodes.Status`), with
    IP address, vendor, machine type, location and other details as attributes.
  - **CPU utilization** (%)
  - **Memory utilization** (%), with total memory (GB) as an attribute
  - **Uptime** — a timestamp of the node's last boot (`Orion.Nodes.LastBoot`),
    so Home Assistant shows how long it's been up as a relative time
  - **Response time** (ms) — disabled by default, diagnostic entity
  - **`<Volume> used`** (%) — one sensor per fixed disk/volume on the node,
    with size/used/free (GB) as attributes
- **Unavailable metrics stay unavailable**: SolarWinds reports `-2` on a
  gauge metric (CPU, memory, response time, volume percent used) when it
  could not collect a value. Rather than show `-2` as a reading, the
  affected sensor goes unavailable until SolarWinds reports a real value.
- **Cross-integration device matching**: when SolarWinds can determine a
  node's MAC address (via the NPM module's interface data, if licensed),
  it's attached to the device as a network connection. Other integrations
  that identify the same physical device by MAC — e.g. **UniFi Network** —
  will merge into the same Home Assistant device instead of creating a
  second one.
- **Web Console link**: each device's "Visit device" link opens the node's
  details page directly in the SolarWinds Web Console.
- New nodes and volumes discovered by SolarWinds are automatically added as
  entities on the next poll — no reconfiguration needed.

## Requirements

- SolarWinds Observability Self-Hosted (Orion Platform), release 2023.1 or
  later, with the SWIS REST API reachable on port **17774**.
- An Orion account (local or Active Directory) with permission to read
  `Orion.Nodes` and `Orion.Volumes`. A dedicated, least-privilege, read-only
  account is recommended — see
  [accounts-and-permissions](https://github.com/trooperthorn/SolarWinds_OrionGuides/blob/main/docs/automation/accounts-and-permissions.md).

## Installation

### HACS (recommended)

1. In HACS, add this repository as a custom repository (category: Integration).
2. Install "SolarWinds Observability (SWIS)".
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/swis` into your Home Assistant `config/custom_components/`
   directory.
2. Restart Home Assistant.

## Configuration

Configuration is done entirely through the UI:

1. Go to **Settings → Devices & Services → Add Integration**, and search for
   **SolarWinds Observability (SWIS)**.
2. Enter:
   - **Host or IP address** of the SolarWinds server
   - **SWIS REST port** (default `17774`)
   - **Username** / **Password** — an Orion local or AD account
   - **Verify SSL certificate** — SWIS presents a self-signed certificate by
     default; see the note below
   - **Web Console URL** (optional) — the base URL of the SolarWinds Web
     Console used to build the device links, e.g. `https://orion.example.com`.
     Defaults to `https://<host>` if left blank.

After setup, use the integration's **Configure** option to set the polling
interval and which volume types (e.g. `Fixed Disk`) are exposed as sensors.

### About TLS

By default SWIS presents a self-signed certificate. If your server uses one
and you don't want to disable verification, issue it a certificate from your
internal CA (or your public CA) and Home Assistant's normal certificate trust
will apply. Turning off "Verify SSL certificate" is supported for lab/test
setups, but the connection carries your SolarWinds credentials, so prefer a
trusted certificate in production.

## How it works

The integration polls the SWIS REST `/Query` endpoint (`POST .../Json/Query`)
with parameterized SWQL, authenticating over HTTP Basic Auth as documented in
the [SWIS REST API guide](https://github.com/trooperthorn/SolarWinds_OrionGuides/blob/main/docs/swis/rest-api.md).
It is entirely read-only — no writes are made to your SolarWinds server.

Two queries run each poll:

- `SELECT ... FROM Orion.Nodes` for node inventory, status and performance
- `SELECT ... FROM Orion.Volumes WHERE VolumeType IN @volumeTypes` for disk
  capacity, joined to nodes by `NodeID`

## Brand assets

`icon.png`/`logo.png` at the repo root are used by HACS. The native Home
Assistant integration-picker icon requires a one-time submission to
[home-assistant/brands](https://github.com/home-assistant/brands); see
[`brands/README.md`](brands/README.md) for the prepared assets and steps.

## Credits

Built against the API reference in
[trooperthorn/SolarWinds_OrionGuides](https://github.com/trooperthorn/SolarWinds_OrionGuides).

## License

MIT
