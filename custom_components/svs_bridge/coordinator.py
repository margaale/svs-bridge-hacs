"""Polling coordinator for the SVS Bridge."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SvsBridgeAuthError, SvsBridgeClient, SvsBridgeError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SvsBridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches /api/v1/state on a fixed interval and shares it with entities."""

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
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.info = info  # static /api/v1/info payload

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_state()
        except SvsBridgeAuthError as err:
            # Token revoked or changed: trigger the reauth flow.
            raise ConfigEntryAuthFailed(str(err)) from err
        except SvsBridgeError as err:
            raise UpdateFailed(str(err)) from err
