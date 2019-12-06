'''
Docker Monitor component

For more details about this component, please refer to the documentation at
https://github.com/aneisch/docker_monitor
'''
import logging
import threading
import time
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    EVENT_HOMEASSISTANT_STOP
)
from homeassistant.core import callback
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import slugify as util_slugify

VERSION = '0.0.3'

REQUIREMENTS = ['docker', 'python-dateutil==2.7.5']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'docker_monitor'

CONF_ATTRIBUTION = 'Data provided by Docker'

DOCKER_HANDLE = 'docker_handle'
DATA_DOCKER_API = 'api'
DATA_CONFIG = 'config'

EVENT_CONTAINER = 'container_event'

PRECISION = 2

DEFAULT_URL = 'unix://var/run/docker.sock'
DEFAULT_NAME = 'Docker'

DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)

DOCKER_TYPE = [
    'switch'
]

CONF_CONTAINERS = 'containers'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_NAME, default=DEFAULT_NAME):
            cv.string,
        vol.Optional(CONF_URL, default=DEFAULT_URL):
            cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
            cv.time_period,
        vol.Optional(CONF_CONTAINERS):
            cv.ensure_list,
    })
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    _LOGGER.info("Settings: {}".format(config[DOMAIN]))

    host = config[DOMAIN].get(CONF_URL)

    try:
        api = DockerAPI(host)
    except (ImportError, ConnectionError) as e:
        _LOGGER.info("Error setting up Docker API ({})".format(e))
        return False
    else:
        version = api.get_info()
        _LOGGER.debug("Docker version: {}".format(
            version.get('version', None)))

        hass.data[DOCKER_HANDLE] = {}
        hass.data[DOCKER_HANDLE][DATA_DOCKER_API] = api
        hass.data[DOCKER_HANDLE][DATA_CONFIG] = {
            CONF_NAME: config[DOMAIN][CONF_NAME],
            CONF_CONTAINERS: config[DOMAIN].get(CONF_CONTAINERS, [container.get_name() for container in api.get_containers()]),
            CONF_SCAN_INTERVAL: config[DOMAIN].get(CONF_SCAN_INTERVAL),
        }

        for component in DOCKER_TYPE:
            load_platform(hass, component, DOMAIN, {}, config)

        def monitor_stop(_service_or_event):
            """Stop the monitor thread."""
            _LOGGER.info("Stopping threads for Docker monitor")
            api.exit()

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, monitor_stop)

        return True


"""
Docker API abstraction
"""


class DockerAPI:
    def __init__(self, base_url):
        self._base_url = base_url
        try:
            import docker
        except ImportError as e:
            _LOGGER.error("Missing Docker library ({})".format(e))
            raise ImportError()

        self._containers = {}
        self._event_callback_listeners = []

        try:
            self._client = docker.DockerClient(base_url=self._base_url)
        except Exception as e:
            _LOGGER.error("Can not connect to Docker ({})".format(e))
            raise ConnectionError()

        for container in self._client.containers.list(all=True) or []:
            _LOGGER.debug("Found container: {}".format(container.name))
            self._containers[container.name] = DockerContainerAPI(
                self._client, container.name)

    def exit(self):
        _LOGGER.info("Stopping threads for Docker monitor")
        for container in self._containers.values():
            container.exit()

    def get_info(self):
        version = {}
        try:
            raw_stats = self._client.version()
            version = {
                'version': raw_stats.get('Version', None),
                'api_version': raw_stats.get('ApiVersion', None),
                'os': raw_stats.get('Os', None),
                'arch': raw_stats.get('Arch', None),
                'kernel': raw_stats.get('KernelVersion', None),
            }
        except Exception as e:
            _LOGGER.error("Cannot get Docker version ({})".format(e))

        return version

    def get_containers(self):
        return list(self._containers.values())

    def get_container(self, name):
        container = None
        if name in self._containers:
            container = self._containers[name]
        return container


class DockerContainerAPI:
    def __init__(self, client, name):
        self._client = client
        self._name = name

        self._subscribers = []

        self._container = client.containers.get(self._name)

        self._thread = None
        self._stopper = None

    def get_name(self):
        return self._name

    # Call from DockerAPI
    def exit(self, timeout=None):
        """Stop the thread."""
        _LOGGER.debug("Close stats thread for container {}".format(self._name))
        if self._thread is not None:
            self._stopper.set()

    # Hard coded interval
    def stats(self, callback, interval=60):
        if not self._subscribers:
            self._stopper = threading.Event()
            thread = threading.Thread(target=self._runnable, kwargs={
                                      'interval': interval})
            self._thread = thread
            thread.start()

        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def get_info(self):
        from dateutil import parser

        self._container.reload()
        info = {
            'status': self._container.attrs['State']['Status']
        }

        return info

    def start(self):
        _LOGGER.info("Start container {}".format(self._name))
        self._container.start()

        # Update our stats after sending command so our switch immediately updates
        stats = {}
        stats['info'] = self.get_info()
        self._notify(stats)

    def stop(self, timeout=10):
        _LOGGER.info("Stop container {}".format(self._name))
        self._container.stop(timeout=timeout)

        # Update our stats after sending command so our switch immediately updates
        stats = {}
        stats['info'] = self.get_info()
        self._notify(stats)

    def _notify(self, message):
        _LOGGER.debug("Send notify for container {}".format(self._name))
        for callback in self._subscribers:
            callback(message)

    def _runnable(self, interval):
        from dateutil import parser

        stream = self._container.stats(stream=False)

        # Run a loop to periodically update container status
        while True:
            if self._stopper.isSet():
                break

            stats = {}
            stats['info'] = self.get_info()
            self._notify(stats)
            time.sleep(interval)
