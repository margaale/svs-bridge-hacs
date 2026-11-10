"""The bridge's device: its firmware version follows what the bridge reports."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, frame

from custom_components.svs_bridge.const import DOMAIN

from .conftest import BRIDGE_ID, mock_bridge, setup_bridge, state_with


def device_of(hass: HomeAssistant) -> dr.DeviceEntry | None:
    """The bridge's device, of the (only) SVS Bridge entry: the registry's lookups are per config entry."""
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    return dr.async_get(hass).async_get_device_by_identifier((DOMAIN, BRIDGE_ID), entry.entry_id)


async def test_device_version_follows_the_bridge(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new firmware version goes onto the device, looked up by identifier and config entry: Home
    Assistant warns about device_registry.async_get_device (its identifiers are no longer unique
    across config entries)."""
    # Home Assistant reports each deprecated call site once per process: start afresh.
    monkeypatch.setattr(frame, "_REPORTED_INTEGRATIONS", set())
    mock_bridge(aioclient_mock)
    entry = await setup_bridge(hass)
    assert device_of(hass).sw_version == "0.3.0"

    aioclient_mock.clear_requests()
    mock_bridge(aioclient_mock, state=state_with(bridge={"sw_version": "0.3.1"}))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert device_of(hass).sw_version == "0.3.1"
    assert "async_get_device`" not in caplog.text
