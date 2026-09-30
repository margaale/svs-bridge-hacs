"""Fixtures for the SVS Bridge tests: a bridge answering its /api/v1 as its README describes."""

from __future__ import annotations

import asyncio
import copy
from typing import Any

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant

from custom_components.svs_bridge.api import SvsBridgeClient, SvsBridgeUnsupportedError
from custom_components.svs_bridge.const import CONF_HOST, CONF_TOKEN, DOMAIN, GITHUB_LATEST_RELEASE_URL

pytest_plugins = "pytest_homeassistant_custom_component"

HOST = "10.0.0.7"
TOKEN = "0123456789abcdef" * 4
BRIDGE_ID = "svs-bridge-a0f262e000f0"

INFO: dict[str, Any] = {
    "id": BRIDGE_ID,
    "name": "SVS Bridge",
    "model": "SVS Bridge (ESP32-S3)",
    "manufacturer": "SVS Bridge",
    "sw_version": "0.3.0",
    "hostname": "svs-bridge.local",
    "api_version": 1,
}

STATE: dict[str, Any] = {
    "svs": {
        "connected": True, "firmware": "SVS_FW_1.21", "current_input": 2, "total_inputs": 8,
        "live": True, "inputs_live": True, "send_enabled": True,
        "current_input_name": "Super Nintendo / Super Famicom", "current_input_device": "snes",
    },
    "bridge": {"sw_version": "0.3.0", "rssi": -52, "uptime_s": 3600},
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/svs_bridge in every test."""
    yield


@pytest.fixture(autouse=True)
def no_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge without /api/v1/events, unless a test takes the events fixture: polling."""

    async def unsupported(self, types: str = "state"):
        raise SvsBridgeUnsupportedError("The bridge has no /api/v1/events")
        yield  # an async generator, like the real one

    monkeypatch.setattr(SvsBridgeClient, "async_events", unsupported)


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> asyncio.Queue:
    """What /api/v1/events pushes: put a dict to send it, an exception to break the socket, None to
    close it. Each connection reads from the same queue; reconnecting doesn't wait."""
    queue: asyncio.Queue = asyncio.Queue()

    async def from_queue(self, types: str = "state"):
        while True:
            item = await queue.get()
            if item is None:
                return
            if isinstance(item, Exception):
                raise item
            yield item

    monkeypatch.setattr(SvsBridgeClient, "async_events", from_queue)
    monkeypatch.setattr("custom_components.svs_bridge.coordinator.RECONNECT_MIN_S", 0)
    monkeypatch.setattr("custom_components.svs_bridge.coordinator.RECONNECT_MAX_S", 0)
    return queue


async def settle(hass: HomeAssistant) -> None:
    """Let the events listener (a background task, which async_block_till_done skips) take what's queued."""
    for _ in range(20):
        await asyncio.sleep(0)
    await hass.async_block_till_done()


def mock_bridge(aioclient_mock: AiohttpClientMocker, *, state: dict[str, Any] | None = None) -> None:
    """Register the bridge's GET routes, and GitHub's latest release."""
    aioclient_mock.get(f"https://{HOST}/api/v1/info", json=INFO)
    aioclient_mock.get(f"https://{HOST}/api/v1/state", json=state or STATE)
    aioclient_mock.get(GITHUB_LATEST_RELEASE_URL, json={"tag_name": "v0.3.0", "html_url": "https://github.com/margaale/svs-bridge/releases/tag/v0.3.0"})


def state_with(**blocks: dict[str, Any]) -> dict[str, Any]:
    """STATE with some of its blocks' keys changed: state_with(svs={"current_input": 3})."""
    state = copy.deepcopy(STATE)
    for block, values in blocks.items():
        state[block].update(values)
    return state


async def setup_bridge(hass: HomeAssistant) -> MockConfigEntry:
    """Add an SVS Bridge config entry and set it up."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST, CONF_TOKEN: TOKEN}, unique_id=BRIDGE_ID, title="SVS Bridge")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
