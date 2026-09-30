"""Coordinator for the SVS Bridge: pushed state over /api/v1/events, polling as a safety net."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SvsBridgeAuthError, SvsBridgeClient, SvsBridgeError, SvsBridgeUnsupportedError
from .const import (
    DOMAIN,
    GITHUB_LATEST_RELEASE_URL,
    LATEST_CHECK_INTERVAL,
    PUSH_UPDATE_INTERVAL,
    RECONNECT_MAX_S,
    RECONNECT_MIN_S,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class SvsBridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Shares the bridge's /api/v1/state with entities: pushed over /api/v1/events as it changes,
    polled as a safety net (or every 3 s with a bridge from before events)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SvsBridgeClient,
        info: dict[str, Any],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.info = info  # static /api/v1/info payload
        # Latest firmware release on GitHub (checked occasionally, not every poll).
        self.latest_version: str | None = None
        self.latest_release_url: str | None = None
        self._latest_checked: datetime | None = None
        self._github = async_get_clientsession(hass)  # verified TLS for github.com
        self._device_version: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.async_get_state()
        except SvsBridgeAuthError as err:
            # Token revoked or changed: trigger the reauth flow.
            raise ConfigEntryAuthFailed(str(err)) from err
        except SvsBridgeError as err:
            raise UpdateFailed(str(err)) from err

        self._update_device_version(data)
        await self._maybe_check_latest()
        return data

    async def async_listen(self) -> None:
        """Keep the bridge's events socket open for as long as the entry is loaded.

        While it's open, each state the bridge pushes updates the entities at once and polling
        slows to a safety net; when it breaks, polling speeds up again until it reconnects. A
        rejected token starts the reauth flow; a bridge from before /api/v1/events is left to
        polling.
        """
        delay = RECONNECT_MIN_S
        while True:
            try:
                async for event in self.client.async_events("state"):
                    kind = event.get("type")
                    if kind == "hello":
                        if "state" in event.get("subscribed", []):
                            self.update_interval = PUSH_UPDATE_INTERVAL
                        delay = RECONNECT_MIN_S
                    elif kind == "state" and isinstance(event.get("state"), dict):
                        self._update_device_version(event["state"])
                        self.async_set_updated_data(event["state"])
                    # Other types (a later bridge's) only come to sockets that ask for them.
            except SvsBridgeAuthError:
                self.update_interval = UPDATE_INTERVAL
                self.config_entry.async_start_reauth(self.hass)
                return
            except SvsBridgeUnsupportedError:
                _LOGGER.debug("The bridge has no /api/v1/events (older firmware): polling")
                return
            except SvsBridgeError as err:
                _LOGGER.debug("The bridge's events socket: %s", err)
            self.update_interval = UPDATE_INTERVAL
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_S)

    def _update_device_version(self, data: dict[str, Any]) -> None:
        """Keep the device's firmware version current as the bridge reports it."""
        version = data.get("bridge", {}).get("sw_version")
        if not version or version == self._device_version:
            return
        self._device_version = version
        device = dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, self.info["id"])})
        if device is not None:
            dr.async_get(self.hass).async_update_device(device.id, sw_version=version)

    async def _maybe_check_latest(self) -> None:
        """Check GitHub for a newer firmware release, at most every 30 minutes."""
        now = dt_util.utcnow()
        if self._latest_checked is not None and now - self._latest_checked < LATEST_CHECK_INTERVAL:
            return
        self._latest_checked = now  # set first, so a failure does not retry in a loop
        try:
            async with self._github.get(
                GITHUB_LATEST_RELEASE_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return
                body = await resp.json()
        except (aiohttp.ClientError, TimeoutError):
            _LOGGER.debug("Could not check GitHub for a newer firmware release", exc_info=True)
            return

        tag = (body.get("tag_name") or "").lstrip("v")
        if tag:
            self.latest_version = tag
            self.latest_release_url = body.get("html_url")
