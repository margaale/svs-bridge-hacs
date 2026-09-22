# SVS Bridge — Home Assistant integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for the
**SVS Bridge**, an ESP32-S3 that connects to an SVS (Scalable Video Switch) over
USB and exposes its state on your network. Use it to react to input changes —
for example, turn on a TV or a RetroTINK when the active input switches.

The integration is **local polling** only: it talks to the bridge over your LAN,
with no cloud and no MQTT.

## Entities

Once set up, the bridge appears as a single device with:

| Entity | Type | Notes |
| --- | --- | --- |
| **Active input** | sensor | The SVS's current input number (`unknown` when no input is active). |
| **Firmware** | update | The bridge's running firmware, and whether a newer GitHub release exists. Notify-only; install from the bridge's web UI. |
| **SVS connected** | binary sensor | Whether the SVS is reachable over the bridge's USB link. |
| **SVS firmware** | sensor (diagnostic) | The SVS firmware version reported in its banner. |
| **Total inputs** | sensor (diagnostic, disabled by default) | How many inputs the SVS has. |
| **Signal strength** | sensor (diagnostic, disabled by default) | The bridge's WiFi RSSI. |

Automate on **Active input** to switch on downstream gear.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository** (category: *Integration*).
2. Install **SVS Bridge** and restart Home Assistant.

### Manual

Copy `custom_components/svs_bridge` into your Home Assistant `config/custom_components/`
directory and restart.

## Setup

The bridge advertises itself over mDNS, so Home Assistant usually **discovers it
automatically** — look for a notification and click *Configure*.

To add it manually: **Settings → Devices & services → Add integration → SVS Bridge**,
then enter the host (e.g. `svs-bridge.local`) and the API token.

**Getting the API token:** open the bridge's web UI, go to the *Home Assistant*
section, and copy the token. If you regenerate it there, Home Assistant will ask
you to re-enter it.

> The bridge uses HTTPS with a self-signed certificate. The integration does not
> verify the certificate (it is a LAN device); the API token is what
> authenticates the connection.

## The bridge firmware

This repository holds only the Home Assistant integration. The ESP32 firmware
that runs on the bridge itself lives at
[margaale/svs-bridge](https://github.com/margaale/svs-bridge).
