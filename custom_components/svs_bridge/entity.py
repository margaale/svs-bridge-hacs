"""Base entity for the SVS Bridge integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .coordinator import SvsBridgeCoordinator


class SvsBridgeEntity(CoordinatorEntity[SvsBridgeCoordinator]):
    """Common device info and availability for all SVS Bridge entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SvsBridgeCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.info
        device_id = info["id"]
        self._attr_unique_id = f"{device_id}_{key}"
        host = coordinator.config_entry.data[CONF_HOST]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=info.get("name", "SVS Bridge"),
            manufacturer=info.get("manufacturer", "SVS Bridge"),
            model=info.get("model", "SVS Bridge"),
            sw_version=info.get("sw_version"),
            configuration_url=f"https://{host}",
        )

    @property
    def _svs(self) -> dict:
        """The 'svs' block of the latest /api/v1/state payload."""
        return self.coordinator.data.get("svs", {})

    @property
    def _bridge(self) -> dict:
        """The 'bridge' block of the latest /api/v1/state payload."""
        return self.coordinator.data.get("bridge", {})
