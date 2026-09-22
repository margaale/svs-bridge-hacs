"""Sensor entities for the SVS Bridge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SvsBridgeConfigEntry
from .entity import SvsBridgeEntity


@dataclass(frozen=True, kw_only=True)
class SvsBridgeSensorDescription(SensorEntityDescription):
    """Describes an SVS Bridge sensor and how to read its value from the state."""

    value_fn: Callable[[dict[str, Any], dict[str, Any]], Any]


SENSORS: tuple[SvsBridgeSensorDescription, ...] = (
    SvsBridgeSensorDescription(
        key="active_input",
        translation_key="active_input",
        icon="mdi:video-input-hdmi",
        state_class=SensorStateClass.MEASUREMENT,
        # current_input is null when the SVS reports no active input (input 0).
        value_fn=lambda svs, bridge: svs.get("current_input"),
    ),
    SvsBridgeSensorDescription(
        key="total_inputs",
        translation_key="total_inputs",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda svs, bridge: svs.get("total_inputs"),
    ),
    SvsBridgeSensorDescription(
        key="svs_firmware",
        translation_key="svs_firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda svs, bridge: svs.get("firmware"),
    ),
    SvsBridgeSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda svs, bridge: bridge.get("rssi"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SvsBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SVS Bridge sensors."""
    coordinator = entry.runtime_data
    async_add_entities(SvsBridgeSensor(coordinator, desc) for desc in SENSORS)


class SvsBridgeSensor(SvsBridgeEntity, SensorEntity):
    """A single value read from the bridge's state payload."""

    entity_description: SvsBridgeSensorDescription

    def __init__(self, coordinator, description: SvsBridgeSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._svs, self._bridge)
