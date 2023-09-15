"""
Support for pfsense gateways status monitoring using alexpmorris / pfsense-status-gateways-json script
Check https://github.com/alexpmorris/pfsense-status-gateways-json on how to install it on pfSense

Copyright (c) 2020 Robert Horvath-Arkosi

Licensed under MIT. All rights reserved.

https://github.com/nagyrobi/home-assistant-custom-components-pfsense-gateways
"""

import asyncio
import json
import logging
from datetime import timedelta

import aiohttp
import async_timeout
import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    CONF_RESOURCE,
    CONF_VERIFY_SSL,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "pfsense_gateways"

DEFAULT_NAME = "pfSense gateway"
DEFAULT_RESOURCE = "http://{0}/status_gateways_json.php?key={1}"
DEFAULT_KEY = "pfsense"

CONF_HOST = "host"
CONF_KEY = "key"
CONF_MONITORED_GATEWAYS = "monitored_gateway_interfaces"

SCAN_INTERVAL = timedelta(minutes=2)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_MONITORED_GATEWAYS): vol.All(cv.ensure_list),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_RESOURCE, default=DEFAULT_RESOURCE): cv.string,
        vol.Optional(CONF_KEY, default=DEFAULT_KEY): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the pfSense sensor."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    key = config.get(CONF_KEY)

    resource = config.get(CONF_RESOURCE).format(host, key)

    session = async_get_clientsession(hass, False)
    rest_client = pfSenseClient(session, resource)

    devices = []
    for variable in config[CONF_MONITORED_GATEWAYS]:
        devices.append(pfSensor(rest_client, name, variable))

    async_add_devices(devices, True)


class pfSensor(Entity):
    """Implementation of a pfSensor sensor."""

    def __init__(self, rest_client, name, if_name):
        """Initialize the pfSensor sensor."""
        self.rest_client = rest_client
        self._name = name
        self._state = None
        self.if_name = if_name
        self.gw_name = None
        self.monitorip = None
        self.sourceip = None
        self.delay = None
        self.loss = None
        self.status = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{0} {1}".format(self._name, self.gw_name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Icon of the sensor, if class is None."""
        return "mdi:wan"

    @property
    def device_state_attributes(self):
        attributes = {}
        attributes["name"] = self.gw_name
        attributes["friendlyiface"] = self.if_name
        attributes["sourceip"] = self.sourceip
        attributes["monitorip"] = self.monitorip
        attributes["delay"] = self.delay
        attributes["loss"] = self.loss
        attributes["status"] = self.status

        return attributes

    async def async_update(self):
        """Get the latest data from REST API and update the state."""
        try:
            await self.rest_client.async_update()
        except:  # pfSenseError:
            self._state = STATE_UNAVAILABLE
            self.status = "unavailable"
            value = None
            return
        value = self.rest_client.data

        try:
            parsed_json = json.loads(value)
            if not isinstance(parsed_json, dict):
                _LOGGER.warning("JSON result was not a dictionary")
                self._state = STATE_UNAVAILABLE
                self.status = "unavailable"
                return
        except ValueError:
            _LOGGER.warning("REST result could not be parsed as JSON")
            _LOGGER.debug("Erroneous JSON: %s", value)
            self._state = STATE_UNAVAILABLE
            self.status = "unavailable"
            return

        try:
            self.gw_name = parsed_json[self.if_name]["name"]
            self.monitorip = parsed_json[self.if_name]["monitorip"]
            self.sourceip = parsed_json[self.if_name]["sourceip"]
            self.delay = parsed_json[self.if_name]["delay"]
            self.loss = parsed_json[self.if_name]["loss"]
            self.status = parsed_json[self.if_name]["status"]

            if self.status in ["okay", "delay", "online"]:
                self._state = True
            else:
                self._state = False

        except KeyError:
            self._state = STATE_UNAVAILABLE
            self.status = "unavailable"


class pfSenseError(Exception):
    pass


class pfSenseClient(object):
    """Class for handling the data retrieval."""

    def __init__(self, session, resource):
        """Initialize the data object."""
        self._session = session
        self._resource = resource
        self.data = None

    async def async_update(self):
        """Get the latest data from pfSense service."""
        _LOGGER.debug("Get data from %s", str(self._resource))
        try:
            with async_timeout.timeout(30):
                response = await self._session.get(self._resource)
            self.data = await response.text()
            _LOGGER.debug("Received data: %s", str(self.data))
        except aiohttp.ClientError as err:
            _LOGGER.warning("REST request error: {0}".format(err))
            self.data = None
            self._state = STATE_UNAVAILABLE
            self.status = "unavailable"
        #            raise pfSenseError
        except asyncio.TimeoutError:
            _LOGGER.warning("REST request timeout")
            self.data = None
            self._state = STATE_UNAVAILABLE
            self.status = "unavailable"


#            raise pfSenseError


## END
