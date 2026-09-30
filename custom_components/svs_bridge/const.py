"""Constants for the SVS Bridge integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "svs_bridge"

# Config entry keys
CONF_HOST = "host"
CONF_TOKEN = "token"

# The bridge serves its API over HTTPS on 443 with a self-signed certificate.
DEFAULT_PORT = 443

# How often the coordinator polls the bridge without events (a bridge from before
# /api/v1/events, or while its socket is down). Events bring an input change at
# once; 10 s (as Cruller's integration) keeps the ESP32's TLS load light meanwhile,
# and makes it plain when events aren't flowing.
UPDATE_INTERVAL = timedelta(seconds=10)

# While /api/v1/events pushes the state, polling is only a safety net.
PUSH_UPDATE_INTERVAL = timedelta(seconds=60)

# The events socket: reconnect after this many seconds, doubling up to the most
# while it keeps failing.
RECONNECT_MIN_S = 5
RECONNECT_MAX_S = 60

# Zeroconf service the firmware advertises (see wifi_manager.cpp).
ZEROCONF_TYPE = "_svsbridge._tcp.local."

# The firmware's GitHub repository, used to detect a newer bridge release.
GITHUB_REPO = "margaale/svs-bridge"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# How often to check GitHub for a newer firmware release (GitHub allows 60
# unauthenticated calls per hour; this stays well within that).
LATEST_CHECK_INTERVAL = timedelta(minutes=30)
