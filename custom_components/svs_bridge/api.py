"""Thin async client for the SVS Bridge HTTP API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import aiohttp


class SvsBridgeError(Exception):
    """A request to the bridge failed."""


class SvsBridgeAuthError(SvsBridgeError):
    """The API token was missing or rejected (HTTP 401)."""


class SvsBridgeUnsupportedError(SvsBridgeError):
    """The bridge's firmware has no such route (HTTP 404): it predates it."""


class SvsBridgeClient:
    """Talks to a single SVS Bridge over its /api/v1 endpoints.

    The bridge uses HTTPS with a self-signed certificate, so the caller is
    expected to pass a session created with verify_ssl=False.
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str) -> None:
        self._session = session
        self._host = host
        self._base = f"https://{host}"
        self._token = token

    async def _get(self, path: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.get(
                f"{self._base}{path}", headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 401:
                    raise SvsBridgeAuthError("The API token was rejected")
                if resp.status != 200:
                    raise SvsBridgeError(f"{path} returned HTTP {resp.status}")
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SvsBridgeError(f"Cannot reach the bridge: {err!r}") from err

    async def async_get_info(self) -> dict[str, Any]:
        """Device identity and capabilities (stable, read once at setup)."""
        return await self._get("/api/v1/info")

    async def async_get_state(self) -> dict[str, Any]:
        """Live SVS and bridge state (polled)."""
        return await self._get("/api/v1/state")

    async def async_events(self, types: str = "state") -> AsyncIterator[dict[str, Any]]:
        """The bridge's events (GET /api/v1/events, a WebSocket): each message as it comes, "hello" first.

        Ends when the bridge closes the socket. Raises SvsBridgeAuthError when the token is rejected
        (401, or an "auth" message: it was regenerated), SvsBridgeUnsupportedError on a firmware
        without events (404), and SvsBridgeError when the socket can't be opened or breaks.
        """
        url = f"wss://{self._host}/api/v1/events?types={types}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            # The heartbeat pings the bridge (it answers on its own) and notices one that's gone.
            async with self._session.ws_connect(url, headers=headers, heartbeat=20) as ws:
                async for msg in ws:
                    if msg.type is aiohttp.WSMsgType.TEXT:
                        try:
                            event = json.loads(msg.data)
                        except ValueError:
                            continue
                        if not isinstance(event, dict):
                            continue
                        if event.get("type") == "auth":
                            raise SvsBridgeAuthError("The API token was regenerated")
                        yield event
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
        except aiohttp.WSServerHandshakeError as err:
            if err.status == 401:
                raise SvsBridgeAuthError("The API token was rejected") from err
            if err.status == 404:
                raise SvsBridgeUnsupportedError("The bridge has no /api/v1/events: update its firmware") from err
            raise SvsBridgeError(f"The bridge refused the events socket: HTTP {err.status}") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SvsBridgeError(f"The bridge's events socket: {err!r}") from err
