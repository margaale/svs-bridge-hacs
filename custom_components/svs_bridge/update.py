"""Firmware update entity for the SVS Bridge.

Reports the running firmware version and the latest release published on GitHub,
so Home Assistant shows the current version and flags when a newer one exists.
It is notify-only: installing is done from the bridge's own web UI (the OTA
update needs the RetroTINK's HD-15 disconnected, etc.).
"""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SvsBridgeConfigEntry
from .entity import SvsBridgeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SvsBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SVS Bridge firmware update entity."""
    async_add_entities([SvsBridgeUpdate(entry.runtime_data)])


class SvsBridgeUpdate(SvsBridgeEntity, UpdateEntity):
    """Shows the installed firmware and the latest GitHub release."""

    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "firmware_update")

    @property
    def installed_version(self) -> str | None:
        # The polled version; fall back to what was read at setup.
        return self._bridge.get("sw_version") or self.coordinator.info.get("sw_version")

    @property
    def latest_version(self) -> str | None:
        # Until the latest release is known, report the installed one so Home
        # Assistant does not show a spurious update.
        return self.coordinator.latest_version or self.installed_version

    @property
    def release_url(self) -> str | None:
        return self.coordinator.latest_release_url
