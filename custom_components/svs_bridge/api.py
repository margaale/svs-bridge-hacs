"""Thin async client for the SVS Bridge HTTP API."""

from __future__ import annotations

from typing import Any

import aiohttp


class SvsBridgeError(Exception):
    """A request to the bridge failed."""


class SvsBridgeAuthError(SvsBridgeError):
    """The API token was missing or rejected (HTTP 401)."""


class SvsBridgeClient:
    """Talks to a single SVS Bridge over its /api/v1 endpoints.

    The bridge uses HTTPS with a self-signed certificate, so the caller is
    expected to pass a session created with verify_ssl=False.
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, token: str) -> None:
        self._session = session
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
        except aiohttp.ClientError as err:
            raise SvsBridgeError(f"Cannot reach the bridge: {err}") from err

    async def async_get_info(self) -> dict[str, Any]:
        """Device identity and capabilities (stable, read once at setup)."""
        return await self._get("/api/v1/info")

    async def async_get_state(self) -> dict[str, Any]:
        """Live SVS and bridge state (polled)."""
        return await self._get("/api/v1/state")
