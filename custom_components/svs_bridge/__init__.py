"""The SVS Bridge integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import SvsBridgeAuthError, SvsBridgeClient, SvsBridgeError
from .const import CONF_HOST, CONF_TOKEN
from .coordinator import SvsBridgeCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

SvsBridgeConfigEntry = ConfigEntry[SvsBridgeCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SvsBridgeConfigEntry) -> bool:
    """Set up SVS Bridge from a config entry."""
    # The bridge's certificate is self-signed, so verification is disabled for
    # this LAN device; the Bearer token is what authenticates the connection.
    session = async_create_clientsession(hass, verify_ssl=False)
    client = SvsBridgeClient(session, entry.data[CONF_HOST], entry.data[CONF_TOKEN])

    try:
        info = await client.async_get_info()
    except SvsBridgeAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SvsBridgeError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = SvsBridgeCoordinator(hass, entry, client, info)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SvsBridgeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
