"""Config flow for the SVS Bridge integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import SvsBridgeAuthError, SvsBridgeClient, SvsBridgeError
from .const import CONF_HOST, CONF_TOKEN, DOMAIN


class SvsBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SVS Bridge."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._discovered_id: str | None = None
        self._discovered_name: str = "SVS Bridge"

    async def _validate(self, host: str, token: str) -> dict[str, Any]:
        """Return /api/v1/info, raising on connection or auth problems."""
        session = async_create_clientsession(self.hass, verify_ssl=False)
        client = SvsBridgeClient(session, host, token)
        return await client.async_get_info()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: the user types the host and pastes the API token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            token = user_input[CONF_TOKEN]
            try:
                info = await self._validate(host, token)
            except SvsBridgeAuthError:
                errors["base"] = "invalid_auth"
            except SvsBridgeError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=info.get("name", "SVS Bridge"),
                    data={CONF_HOST: host, CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str}
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """A bridge announced itself via mDNS: confirm and ask for the token."""
        self._host = discovery_info.host
        props = discovery_info.properties
        self._discovered_id = props.get("id")
        self._discovered_name = discovery_info.name.split(".")[0] or "SVS Bridge"

        if self._discovered_id:
            await self.async_set_unique_id(self._discovered_id)
            self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the API token to finish a discovered setup."""
        errors: dict[str, str] = {}
        assert self._host is not None
        if user_input is not None:
            token = user_input[CONF_TOKEN]
            try:
                info = await self._validate(self._host, token)
            except SvsBridgeAuthError:
                errors["base"] = "invalid_auth"
            except SvsBridgeError:
                errors["base"] = "cannot_connect"
            else:
                if not self.unique_id:
                    await self.async_set_unique_id(info["id"])
                    self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
                return self.async_create_entry(
                    title=info.get("name", self._discovered_name),
                    data={CONF_HOST: self._host, CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            description_placeholders={"name": self._discovered_name, "host": self._host},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """The token stopped working (e.g. it was regenerated on the bridge)."""
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new token and update the existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN]
            try:
                await self._validate(entry.data[CONF_HOST], token)
            except SvsBridgeAuthError:
                errors["base"] = "invalid_auth"
            except SvsBridgeError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )
