"""Constants for the SVS Bridge integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "svs_bridge"

# Config entry keys
CONF_HOST = "host"
CONF_TOKEN = "token"

# The bridge serves its API over HTTPS on 443 with a self-signed certificate.
DEFAULT_PORT = 443

# How often the coordinator polls the bridge. The SVS reports input changes
# almost immediately over serial; a few seconds of latency is fine for turning
# a TV or scaler on, and keeps the little ESP32 lightly loaded.
UPDATE_INTERVAL = timedelta(seconds=3)

# Zeroconf service the firmware advertises (see wifi_manager.cpp).
ZEROCONF_TYPE = "_svsbridge._tcp.local."
