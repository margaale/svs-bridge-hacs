"""Tests of the events socket (/api/v1/events): pushed state, polling as a safety net, reconnecting,
and a regenerated token."""

from __future__ import annotations

import asyncio

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.svs_bridge.api import SvsBridgeAuthError, SvsBridgeError
from custom_components.svs_bridge.const import DOMAIN, PUSH_UPDATE_INTERVAL, UPDATE_INTERVAL

from .conftest import BRIDGE_ID, mock_bridge, settle, setup_bridge, state_with

HELLO = {"type": "hello", "api_version": 1, "types": ["state"], "subscribed": ["state"]}


def sensor(hass: HomeAssistant, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{BRIDGE_ID}_{key}")
    return hass.states.get(entity_id).state


def active_input(hass: HomeAssistant) -> str:
    return sensor(hass, "active_input")


def updates(hass: HomeAssistant) -> str:
    """The "Updates" diagnostic sensor: push or polling."""
    return sensor(hass, "updates")


async def test_setup_polls(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """A bridge from before /api/v1/events (404): polled every 10 s."""
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    await settle(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.update_interval == UPDATE_INTERVAL
    assert active_input(hass) == "2"
    assert updates(hass) == "polling"


async def test_pushed_state(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, events: asyncio.Queue) -> None:
    """Each state the bridge pushes updates the entities at once; polling slows to a safety net."""
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    events.put_nowait(HELLO)
    events.put_nowait({"type": "state", "state": state_with(svs={"current_input": 5})})
    await settle(hass)
    assert active_input(hass) == "5"
    assert entry.runtime_data.update_interval == PUSH_UPDATE_INTERVAL
    assert updates(hass) == "push"

    # A type a later bridge could send (to sockets that ask for it) changes nothing.
    events.put_nowait({"type": "later", "anything": [1, 2]})
    events.put_nowait({"type": "state", "state": state_with(svs={"current_input": 1})})
    await settle(hass)
    assert active_input(hass) == "1"


async def test_socket_breaks_and_reconnects(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, events: asyncio.Queue
) -> None:
    """While the socket is down, polling speeds up again; once it's back, it slows down."""
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    coordinator = entry.runtime_data
    events.put_nowait(HELLO)
    await settle(hass)
    assert coordinator.update_interval == PUSH_UPDATE_INTERVAL
    assert updates(hass) == "push"  # the hello alone says so, before any state

    events.put_nowait(SvsBridgeError("The bridge restarted"))
    await settle(hass)
    assert coordinator.update_interval == UPDATE_INTERVAL
    assert updates(hass) == "polling"

    events.put_nowait(HELLO)
    events.put_nowait({"type": "state", "state": state_with(svs={"current_input": 7})})
    await settle(hass)
    assert coordinator.update_interval == PUSH_UPDATE_INTERVAL
    assert active_input(hass) == "7"
    assert updates(hass) == "push"

    events.put_nowait(None)  # the bridge closed it: poll until it's back
    await settle(hass)
    assert coordinator.update_interval == UPDATE_INTERVAL


async def test_hello_without_state(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, events: asyncio.Queue
) -> None:
    """A socket that doesn't get "state" (not offered) leaves polling as it is."""
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    events.put_nowait({"type": "hello", "api_version": 1, "types": [], "subscribed": []})
    await settle(hass)
    assert entry.runtime_data.update_interval == UPDATE_INTERVAL
    assert updates(hass) == "polling"


async def test_token_regenerated(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, events: asyncio.Queue
) -> None:
    """The bridge says the token changed ("auth"): Home Assistant asks for the new one, and stops
    listening until it has it."""
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    events.put_nowait(HELLO)
    events.put_nowait(SvsBridgeAuthError("The API token was regenerated"))
    await settle(hass)
    flows = [f for f in hass.config_entries.flow.async_progress() if f["context"]["source"] == SOURCE_REAUTH]
    assert len(flows) == 1
    assert flows[0]["context"]["entry_id"] == entry.entry_id
    assert entry.runtime_data.update_interval == UPDATE_INTERVAL
    assert updates(hass) == "polling"
    events.put_nowait({"type": "state", "state": state_with(svs={"current_input": 4})})
    await settle(hass)
    assert events.qsize() == 1  # nobody took it: the listener stopped


async def test_unload_stops_listening(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, events: asyncio.Queue
) -> None:
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    events.put_nowait(HELLO)
    await settle(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await settle(hass)
    events.put_nowait({"type": "state", "state": state_with(svs={"current_input": 4})})
    await settle(hass)
    assert events.qsize() == 1
