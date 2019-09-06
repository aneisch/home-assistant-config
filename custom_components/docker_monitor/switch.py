'''
Docker Monitor component

For more details about this component, please refer to the documentation at
https://github.com/Sanderhuisman/home-assistant-custom-components
'''
import logging

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SwitchDevice
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_NAME
)
from homeassistant.core import ServiceCall

from custom_components.docker_monitor import (
    CONF_ATTRIBUTION,
    CONF_CONTAINERS,
    DATA_CONFIG,
    DATA_DOCKER_API,
    DOCKER_HANDLE
)

VERSION = '0.0.3'

DEPENDENCIES = ['docker_monitor']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Set up the Docker Monitor Switch."""

    api = hass.data[DOCKER_HANDLE][DATA_DOCKER_API]
    config = hass.data[DOCKER_HANDLE][DATA_CONFIG]
    clientname = config[CONF_NAME]

    containers = [container.get_name() for container in api.get_containers()]
    switches = [ContainerSwitch(api, clientname, name)
                for name in config[CONF_CONTAINERS] if name in containers]
    if switches:
        add_devices_callback(switches, True)
    else:
        _LOGGER.info("No containers setup")
        return False


class ContainerSwitch(SwitchDevice):
    def __init__(self, api, clientname, container_name):
        self._api = api
        self._clientname = clientname
        self._container_name = container_name
        self._state = False

        self._container = api.get_container(container_name)

        def update_callback(stats):
            _LOGGER.debug("Received callback with message: {}".format(stats))

            if stats['info']['status'] == 'running':
                state = True
            else:
                state = False

            if self._state is not state:
                self._state = state

                self.schedule_update_ha_state()

        self._container.stats(update_callback)

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} {}".format(self._clientname, self._container_name)

    @property
    def should_poll(self):
        return True

    @property
    def icon(self):
        return 'mdi:docker'

    @property
    def device_state_attributes(self):
        return {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION
        }

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs):
        self._container.start()

    def turn_off(self, **kwargs):
        self._container.stop()
