"""Config flow for BHyve integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_DEVICES, DEVICE_BRIDGE, DOMAIN
from .pybhyve import Client
from .pybhyve.errors import AuthenticationError, BHyveError

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BHyve."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data: dict = {}
        self.client: Client | None = None
        self.devices: list[Any] | None = None
        self.programs: list[Any] | None = None
        self._reauth_username: str | None = None

    async def async_auth(self, user_input: dict[str, str]) -> dict[str, str] | None:
        """Reusable Auth Helper."""
        self.client = Client(
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
            session=async_get_clientsession(self.hass),
        )

        try:
            result = await self.client.login()
            if result is False:
                return {"base": "invalid_auth"}
            return None
        except AuthenticationError:
            return {"base": "invalid_auth"}
        except Exception:  # pylint: disable=broad-except
            return {"base": "cannot_connect"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] | None = None

        if user_input is not None:
            if not (errors := await self.async_auth(user_input)):
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                self.data = user_input
                self.devices = await self.client.devices  # type: ignore[union-attr]
                self.programs = await self.client.timer_programs  # type: ignore[union-attr]

                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the optional device selection step."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.data[CONF_USERNAME], data=self.data, options=user_input
            )

        device_options = {
            str(d.get("id")): f'{d.get("name", "Unnamed device")}'
            for d in self.devices
            if d.get("type") != DEVICE_BRIDGE
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICES, default=list(device_options.keys())
                    ): cv.multi_select(device_options)
                }
            ),
            errors=None,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth."""
        errors: dict[str, str] | None = None
        if user_input and user_input.get(CONF_USERNAME):
            self._reauth_username = user_input[CONF_USERNAME]

        elif self._reauth_username and user_input and user_input.get(CONF_PASSWORD):
            data = {
                CONF_USERNAME: self._reauth_username,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            if not (errors := await self.async_auth(data)):
                entry = await self.async_set_unique_id(self._reauth_username.lower())
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data=data,
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
                return self.async_create_entry(title=self._reauth_username, data=data)

        return self.async_show_form(
            step_id="reauth",
            description_placeholders={"username": self._reauth_username},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, config):
        """Handle import of BHyve config from YAML."""

        username = config[CONF_USERNAME]
        password = config[CONF_PASSWORD]

        credentials = {
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
        }

        if not (errors := await self.async_auth(credentials)):
            await self.async_set_unique_id(credentials[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            self.data = credentials
            self.devices = await self.client.devices  # type: ignore[union-attr]
            self.programs = await self.client.timer_programs  # type: ignore[union-attr]

            devices = [str(d["id"]) for d in self.devices if d["type"] != DEVICE_BRIDGE]

            return await self.async_step_device(user_input={CONF_DEVICES: devices})

        return self.async_abort(reason="cannot_connect")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for picking devices."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        if self.config_entry.state != config_entries.ConfigEntryState.LOADED:
            return self.async_abort(reason="unknown")

        data = self.hass.data[DOMAIN][self.config_entry.entry_id]
        try:
            client = data["client"]
            result = await client.login()
            if result is False:
                return self.async_abort(reason="invalid_auth")

            devices = await client.devices
        except AuthenticationError:
            return self.async_abort(reason="invalid_auth")
        except BHyveError:
            return self.async_abort(reason="cannot_connect")

        _LOGGER.debug("Devices: %s", json.dumps(devices))

        # _LOGGER.debug("ALL DEVICES")
        # _LOGGER.debug(str(self.config_entry.options))

        device_options = {
            str(d.get("id")): f'{d.get("name", "Unnamed device")}'
            for d in devices
            if d.get("type") != DEVICE_BRIDGE
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICES,
                        default=self.config_entry.options.get(CONF_DEVICES),
                    ): cv.multi_select(device_options),
                }
            ),
        )
