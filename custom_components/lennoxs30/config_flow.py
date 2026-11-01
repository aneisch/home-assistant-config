"""Integration Configuration."""

# pylint: disable=attribute-defined-outside-init
# pylint: disable=line-too-long
# pylint: disable=missing-function-docstring
from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from lennoxs30api.s30exception import EC_LOGIN, S30Exception

from . import Manager
from .const import (
    CONF_ALLERGEN_DEFENDER_SWITCH,
    CONF_APP_ID,
    CONF_CLOUD_CONNECTION,
    CONF_CREATE_DIAGNOSTICS_SENSORS,
    CONF_CREATE_INVERTER_POWER,
    CONF_CREATE_PARAMETERS,
    CONF_CREATE_SENSORS,
    CONF_FAST_POLL_COUNT,
    CONF_FAST_POLL_INTERVAL,
    CONF_INIT_WAIT_TIME,
    CONF_LOCAL_CONNECTION,
    CONF_LOG_MESSAGES_TO_FILE,
    CONF_MESSAGE_DEBUG_FILE,
    CONF_MESSAGE_DEBUG_LOGGING,
    CONF_PII_IN_MESSAGE_LOGS,
    DEFAULT_CLOUD_TIMEOUT,
    DEFAULT_LOCAL_TIMEOUT,
    LENNOX_DEFAULT_CLOUD_APP_ID,
    LENNOX_DEFAULT_LOCAL_APP_ID,
)
from .util import dict_redact_fields, redact_email

DEFAULT_POLL_INTERVAL: int = 10
DEFAULT_FAST_POLL_INTERVAL: float = 0.75
DEFAULT_FAST_POLL_COUNT: int = 10
MAX_ERRORS = 5
RETRY_INTERVAL_SECONDS = 60
DOMAIN = "lennoxs30"
_LOGGER = logging.getLogger(__name__)


STEP_ONE = vol.Schema(
    {
        vol.Required(CONF_LOCAL_CONNECTION, default=True): cv.boolean,
        vol.Required(CONF_CLOUD_CONNECTION, default=False): cv.boolean,
    }
)

STEP_CLOUD = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_APP_ID, default=LENNOX_DEFAULT_CLOUD_APP_ID): cv.string,
        vol.Optional(CONF_CREATE_SENSORS, default=True): cv.boolean,
        vol.Optional(CONF_ALLERGEN_DEFENDER_SWITCH, default=False): cv.boolean,
    }
)

STEP_LOCAL = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_APP_ID, default=LENNOX_DEFAULT_LOCAL_APP_ID): cv.string,
        vol.Optional(CONF_CREATE_SENSORS, default=True): cv.boolean,
        vol.Optional(CONF_ALLERGEN_DEFENDER_SWITCH, default=False): cv.boolean,
        vol.Optional(CONF_CREATE_INVERTER_POWER, default=False): cv.boolean,
        vol.Optional(CONF_CREATE_DIAGNOSTICS_SENSORS, default=False): cv.boolean,
        vol.Optional(CONF_CREATE_PARAMETERS, default=False): cv.boolean,
        vol.Optional(CONF_PROTOCOL, default="https"): cv.string,
    }
)


def host_valid(hostport: str) -> bool:
    """Return True if hostname or IP address is valid."""
    # We allow an host:port syntax.
    splits = hostport.split(":")
    host = splits[0]
    try:
        if ipaddress.ip_address(host).version == (4 or 6):
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))


@callback
def lennox30_entries(hass: HomeAssistant) -> set:
    """Return the hosts already configured."""
    return {entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN) if CONF_HOST in entry.data}


class Lennoxs30ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Lennox S30 configflow."""

    VERSION = 5
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _host_in_configuration_exists(self, host: str) -> bool:
        """Return True if host exists in configuration."""
        return host in lennox30_entries(self.hass)

    def get_advanced_schema(self, is_cloud: bool) -> vol.Schema:
        """Return the schema based on whether cloud or local."""
        if is_cloud:
            scan_interval = 15
            conf_wait_time = 60
            timeout = DEFAULT_CLOUD_TIMEOUT
        else:
            scan_interval = 1
            conf_wait_time = 30
            timeout = DEFAULT_LOCAL_TIMEOUT
        return vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Optional(CONF_FAST_POLL_INTERVAL, default=DEFAULT_FAST_POLL_INTERVAL): vol.All(
                    vol.Coerce(float), vol.Range(min=0.25, max=300.0)
                ),
                vol.Optional(CONF_FAST_POLL_COUNT, default=DEFAULT_FAST_POLL_COUNT): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                vol.Optional(CONF_INIT_WAIT_TIME, default=conf_wait_time): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Optional(CONF_TIMEOUT, default=timeout): vol.All(vol.Coerce(int), vol.Range(min=15, max=300)),
                vol.Optional(CONF_PII_IN_MESSAGE_LOGS, default=False): cv.boolean,
                vol.Optional(CONF_MESSAGE_DEBUG_LOGGING, default=True): cv.boolean,
                vol.Optional(CONF_LOG_MESSAGES_TO_FILE, default=False): cv.boolean,
                vol.Optional(CONF_MESSAGE_DEBUG_FILE, default=""): cv.string,
            }
        )

    async def async_step_user(self, user_input: None | dict[str, Any] = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        self.config_input = {}
        _LOGGER.debug("async_step_user user_input [%s]", dict_redact_fields(user_input))
        if user_input is not None:
            cloud_connection = user_input[CONF_CLOUD_CONNECTION]
            local_connection = user_input[CONF_LOCAL_CONNECTION]
            if cloud_connection == local_connection:
                errors[CONF_LOCAL_CONNECTION] = "select_cloud_or_local"
            else:
                update_dict = {CONF_CLOUD_CONNECTION: cloud_connection}
                self.config_input.update(update_dict)
                if cloud_connection:
                    return await self.async_step_cloud()
                return await self.async_step_local()

        return self.async_show_form(step_id="user", data_schema=STEP_ONE, errors=errors)

    async def async_step_cloud(self, user_input: None | dict[str, Any] = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        _LOGGER.debug("async_step_cloud user_input [%s]", dict_redact_fields(user_input))
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN + "_" + user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()
            try:
                await self.try_to_connect(user_input)
                self.config_input.update(user_input)
                return await self.async_step_advanced()
            except S30Exception as ex:
                _LOGGER.exception("async_step_cloud error")
                if ex.error_code == EC_LOGIN:
                    errors["base"] = "unable_to_connect_login"
                else:
                    errors["base"] = "unable_to_connect_cloud"
        return self.async_show_form(step_id="cloud", data_schema=STEP_CLOUD, errors=errors)

    async def async_step_local(self, user_input: None | dict[str, Any] = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        _LOGGER.debug("async_step_local user_input [%s]", dict_redact_fields(user_input))

        if user_input is not None:
            host = user_input[CONF_HOST]
            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_hostname"
            else:
                await self.async_set_unique_id(DOMAIN + "_" + user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                try:
                    await self.try_to_connect(user_input)
                    self.config_input.update(user_input)
                    return await self.async_step_advanced()
                except S30Exception:
                    _LOGGER.exception("async_step_local error")
                    errors[CONF_HOST] = "unable_to_connect_local"
        return self.async_show_form(step_id="local", data_schema=STEP_LOCAL, errors=errors)

    async def async_step_advanced(self, user_input: None | dict[str, Any] = None) -> ConfigFlowResult:
        """Handle advanced configuration."""
        errors = {}
        _LOGGER.debug("async_step_advanced user_input [%s]", dict_redact_fields(user_input))

        if user_input is not None:
            self.config_input.update(user_input)
            return await self.create_entry()
        return self.async_show_form(
            step_id="advanced",
            data_schema=self.get_advanced_schema(self.config_input[CONF_CLOUD_CONNECTION]),
            errors=errors,
        )

    async def create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        if self.config_input[CONF_CLOUD_CONNECTION]:
            title = redact_email(self.config_input[CONF_EMAIL])
        else:
            title = self.config_input[CONF_HOST]
        await self.async_set_unique_id(DOMAIN + "_" + title)
        self._abort_if_unique_id_configured()
        if self.config_input[CONF_LOG_MESSAGES_TO_FILE] is False:
            self.config_input[CONF_MESSAGE_DEBUG_FILE] = ""
        _LOGGER.debug("async_step_advanced config_input [%s]", dict_redact_fields(self.config_input))
        return self.async_create_entry(title=title, data=self.config_input)

    async def try_to_connect(self, user_input: dict[str, Any]) -> None:
        """Determine if account or device is reachable."""
        if self.config_input[CONF_CLOUD_CONNECTION]:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            ip_address = None
            protocol = "https"
            timeout = DEFAULT_CLOUD_TIMEOUT
        else:
            email = None
            password = None
            ip_address = user_input[CONF_HOST]
            protocol = user_input[CONF_PROTOCOL]
            timeout = DEFAULT_LOCAL_TIMEOUT

        self.manager = Manager(
            hass=self.hass,
            config=None,
            email=email,
            password=password,
            poll_interval=1,
            fast_poll_interval=1.0,
            allergen_defender_switch=False,
            app_id=user_input[CONF_APP_ID],
            conf_init_wait_time=30,
            ip_address=ip_address,
            create_sensors=False,
            create_inverter_power=False,
            protocol=protocol,
            pii_message_logs=False,
            message_debug_logging=True,
            message_logging_file=None,
            timeout=timeout,
            fast_poll_count=10,
        )
        await self.manager.connect()
        await self.manager.async_shutdown(None)

    async def async_step_import(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle the import step."""
        self.config_input = {}
        _LOGGER.debug("async_step_import user_input [%s]", dict_redact_fields(user_input))
        self.config_input.update(user_input)
        return await self.create_entry()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Class to handle options flow."""

    async def async_step_init(self, user_input: None | dict[str, Any] = None) -> ConfigFlowResult:
        """Manage the options."""
        _LOGGER.debug(
            "OptionsFlowHandler:async_step_init user_input [%s] data [%s]",
            dict_redact_fields(user_input),
            dict_redact_fields(self.config_entry.data),
        )
        if user_input is not None:
            if CONF_HOST in self.config_entry.data:
                user_input[CONF_HOST] = self.config_entry.data[CONF_HOST]
            if CONF_EMAIL in self.config_entry.data:
                user_input[CONF_EMAIL] = self.config_entry.data[CONF_EMAIL]
            if CONF_CLOUD_CONNECTION in self.config_entry.data:
                user_input[CONF_CLOUD_CONNECTION] = self.config_entry.data[CONF_CLOUD_CONNECTION]
            if user_input[CONF_LOG_MESSAGES_TO_FILE] is False:
                user_input[CONF_MESSAGE_DEBUG_FILE] = ""

            self.hass.config_entries.async_update_entry(self.config_entry, data=user_input, options=self.config_entry.options)
            return self.async_create_entry(title="", data={})

        if self.config_entry.data[CONF_CLOUD_CONNECTION] is False:
            # Local Connection
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_APP_ID, default=self.config_entry.data[CONF_APP_ID]): cv.string,
                        vol.Optional(
                            CONF_CREATE_SENSORS,
                            default=self.config_entry.data[CONF_CREATE_SENSORS],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_ALLERGEN_DEFENDER_SWITCH,
                            default=self.config_entry.data[CONF_ALLERGEN_DEFENDER_SWITCH],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_CREATE_INVERTER_POWER,
                            default=self.config_entry.data[CONF_CREATE_INVERTER_POWER],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_CREATE_DIAGNOSTICS_SENSORS,
                            default=self.config_entry.data[CONF_CREATE_DIAGNOSTICS_SENSORS],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_CREATE_PARAMETERS,
                            default=self.config_entry.data[CONF_CREATE_PARAMETERS],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_SCAN_INTERVAL,
                            default=self.config_entry.data[CONF_SCAN_INTERVAL],
                        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                        vol.Optional(
                            CONF_INIT_WAIT_TIME,
                            default=self.config_entry.data[CONF_INIT_WAIT_TIME],
                        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                        vol.Optional(
                            CONF_FAST_POLL_INTERVAL,
                            default=self.config_entry.data[CONF_FAST_POLL_INTERVAL],
                        ): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=300.0)),
                        vol.Optional(
                            CONF_FAST_POLL_COUNT,
                            default=self.config_entry.data[CONF_FAST_POLL_COUNT],
                        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                        vol.Optional(CONF_TIMEOUT, default=self.config_entry.data[CONF_TIMEOUT]): vol.All(
                            vol.Coerce(int), vol.Range(min=15, max=300)
                        ),
                        vol.Optional(CONF_PROTOCOL, default=self.config_entry.data[CONF_PROTOCOL]): cv.string,
                        vol.Optional(
                            CONF_PII_IN_MESSAGE_LOGS,
                            default=self.config_entry.data[CONF_PII_IN_MESSAGE_LOGS],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_MESSAGE_DEBUG_LOGGING,
                            default=self.config_entry.data[CONF_MESSAGE_DEBUG_LOGGING],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_LOG_MESSAGES_TO_FILE,
                            default=self.config_entry.data[CONF_LOG_MESSAGES_TO_FILE],
                        ): cv.boolean,
                        vol.Optional(
                            CONF_MESSAGE_DEBUG_FILE,
                            default=self.config_entry.data[CONF_MESSAGE_DEBUG_FILE],
                        ): cv.string,
                    }
                ),
            )
        # Cloud Connection
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PASSWORD,
                        default=self.config_entry.data[CONF_PASSWORD],
                    ): cv.string,
                    vol.Optional(CONF_APP_ID, default=self.config_entry.data[CONF_APP_ID]): cv.string,
                    vol.Optional(
                        CONF_CREATE_SENSORS,
                        default=self.config_entry.data[CONF_CREATE_SENSORS],
                    ): cv.boolean,
                    vol.Optional(
                        CONF_ALLERGEN_DEFENDER_SWITCH,
                        default=self.config_entry.data[CONF_ALLERGEN_DEFENDER_SWITCH],
                    ): cv.boolean,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.data[CONF_SCAN_INTERVAL],
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_INIT_WAIT_TIME,
                        default=self.config_entry.data[CONF_INIT_WAIT_TIME],
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                    vol.Optional(
                        CONF_FAST_POLL_INTERVAL,
                        default=self.config_entry.data[CONF_FAST_POLL_INTERVAL],
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=300.0)),
                    vol.Optional(
                        CONF_FAST_POLL_COUNT,
                        default=self.config_entry.data[CONF_FAST_POLL_COUNT],
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                    vol.Optional(CONF_TIMEOUT, default=self.config_entry.data[CONF_TIMEOUT]): vol.All(
                        vol.Coerce(int), vol.Range(min=15, max=300)
                    ),
                    vol.Optional(
                        CONF_PII_IN_MESSAGE_LOGS,
                        default=self.config_entry.data[CONF_PII_IN_MESSAGE_LOGS],
                    ): cv.boolean,
                    vol.Optional(
                        CONF_MESSAGE_DEBUG_LOGGING,
                        default=self.config_entry.data[CONF_MESSAGE_DEBUG_LOGGING],
                    ): cv.boolean,
                    vol.Optional(
                        CONF_LOG_MESSAGES_TO_FILE,
                        default=self.config_entry.data[CONF_LOG_MESSAGES_TO_FILE],
                    ): cv.boolean,
                    vol.Optional(
                        CONF_MESSAGE_DEBUG_FILE,
                        default=self.config_entry.data[CONF_MESSAGE_DEBUG_FILE],
                    ): cv.string,
                }
            ),
        )
