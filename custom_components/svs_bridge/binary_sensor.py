"""Binary sensor entities for the SVS Bridge."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SvsBridgeConfigEntry
from .entity import SvsBridgeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SvsBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SVS Bridge binary sensors."""
    async_add_entities([SvsConnectedBinarySensor(entry.runtime_data)])


class SvsConnectedBinarySensor(SvsBridgeEntity, BinarySensorEntity):
    """Whether the SVS is currently reachable over the bridge's USB link."""

    _attr_translation_key = "svs_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "svs_connected")

    @property
    def is_on(self) -> bool:
        return bool(self._svs.get("connected"))
