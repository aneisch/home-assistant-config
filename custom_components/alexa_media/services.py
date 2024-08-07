"""
Alexa Services.

SPDX-License-Identifier: Apache-2.0

For more details about this platform, please refer to the documentation at
https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639
"""

import logging
from typing import Callable

from alexapy import AlexaAPI, AlexapyLoginError, hide_email
from alexapy.errors import AlexapyConnectionError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    ATTR_EMAIL,
    ATTR_NUM_ENTRIES,
    DATA_ALEXAMEDIA,
    DOMAIN,
    SERVICE_FORCE_LOGOUT,
    SERVICE_UPDATE_LAST_CALLED,
)
from .helpers import _catch_login_errors, report_relogin_required

_LOGGER = logging.getLogger(__name__)


FORCE_LOGOUT_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)
LAST_CALL_UPDATE_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_EMAIL, default=[]): vol.All(cv.ensure_list, [cv.string])}
)


class AlexaMediaServices:
    """Class that holds our services that should be published to hass."""

    def __init__(self, hass, functions: dict[str, Callable]):
        """Initialize with self.hass."""
        self.hass = hass
        self.functions: dict[str, Callable] = functions

    async def register(self):
        """Register services to hass."""
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_LAST_CALLED,
            self.last_call_handler,
            schema=LAST_CALL_UPDATE_SCHEMA,
        )
        self.hass.services.async_register(
            DOMAIN, SERVICE_FORCE_LOGOUT, self.force_logout, schema=FORCE_LOGOUT_SCHEMA
        )

    async def unregister(self):
        """Register services to hass."""
        self.hass.services.async_remove(
            DOMAIN,
            SERVICE_UPDATE_LAST_CALLED,
        )
        self.hass.services.async_remove(DOMAIN, SERVICE_FORCE_LOGOUT)

    @_catch_login_errors
    async def force_logout(self, call) -> bool:
        """Handle force logout service request.

        Arguments
            call.ATTR_EMAIL {List[str: None]} -- Case-sensitive Alexa emails.
                                                    Default is all known emails.

        Returns
            bool -- True if force logout successful

        """
        requested_emails = call.data.get(ATTR_EMAIL)

        _LOGGER.debug("Service force_logout called for: %s", requested_emails)
        success = False
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
            try:
                await AlexaAPI.force_logout()
            except AlexapyLoginError:
                report_relogin_required(self.hass, login_obj, email)
                success = True
            except AlexapyConnectionError:
                _LOGGER.error(
                    "Unable to connect to Alexa for %s;"
                    " check your network connection and try again",
                    hide_email(email),
                )
        return success

    async def last_call_handler(self, call):
        """Handle last call service request.

        Args
        call: List of case-sensitive Alexa email addresses. If None
                            all accounts are updated.

        """
        requested_emails = call.data.get(ATTR_EMAIL)
        _LOGGER.debug("Service update_last_called for: %s", requested_emails)
        for email, account_dict in self.hass.data[DATA_ALEXAMEDIA]["accounts"].items():
            if requested_emails and email not in requested_emails:
                continue
            login_obj = account_dict["login_obj"]
            try:
                await self.functions.get("update_last_called")(login_obj)
            except AlexapyLoginError:
                report_relogin_required(self.hass, login_obj, email)
            except AlexapyConnectionError:
                _LOGGER.error(
                    "Unable to connect to Alexa for %s;"
                    " check your network connection and try again",
                    hide_email(email),
                )
