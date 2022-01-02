"""Sensor for keymaster."""
import json
import logging
from typing import List

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorEntity,
)
from homeassistant.components.mqtt import async_subscribe, models
from homeassistant.core import callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify

from .const import (
    CHILD_LOCKS,
    DOMAIN,
    OZW_READY_STATUSES,
    OZW_STATUS_KEY,
    OZW_STATUS_TOPIC,
    PRIMARY_LOCK,
)
from .helpers import (
    async_update_zwave_js_nodes_and_devices,
    async_using_ozw,
    async_using_zwave,
    async_using_zwave_js,
)
from .lock import KeymasterLock

try:
    from homeassistant.components.zwave_js.const import (
        DATA_CLIENT as ZWAVE_JS_DATA_CLIENT,
        DOMAIN as ZWAVE_JS_DOMAIN,
    )
except (ModuleNotFoundError, ImportError):
    pass

try:
    from homeassistant.components.ozw.const import DOMAIN as OZW_DOMAIN
except (ModuleNotFoundError, ImportError):
    pass

try:
    from openzwave.network import ZWaveNetwork
    from pydispatch import dispatcher

    from homeassistant.components.zwave.const import (
        DATA_NETWORK as ZWAVE_DATA_NETWORK,
        DOMAIN as ZWAVE_DOMAIN,
    )

    ZWAVE_NETWORK_READY_STATUSES = (
        ZWaveNetwork.SIGNAL_AWAKE_NODES_QUERIED,
        ZWaveNetwork.SIGNAL_ALL_NODES_QUERIED,
        ZWaveNetwork.SIGNAL_ALL_NODES_QUERIED_SOME_DEAD,
        ZWaveNetwork.SIGNAL_NETWORK_READY,
    )
    ZWAVE_NETWORK_NOT_READY_STATUSES = (
        ZWaveNetwork.SIGNAL_NETWORK_FAILED,
        ZWaveNetwork.SIGNAL_NETWORK_STOPPED,
        ZWaveNetwork.SIGNAL_NETWORK_RESETTED,
    )
except (ModuleNotFoundError, ImportError):
    pass

_LOGGER = logging.getLogger(__name__)
ENTITY_NAME = "Network"


def generate_binary_sensor_name(lock_name: str) -> str:
    """Generate unique ID for network ready sensor."""
    return f"{lock_name}: {ENTITY_NAME}"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup config entry."""
    primary_lock = hass.data[DOMAIN][config_entry.entry_id][PRIMARY_LOCK]
    child_locks = hass.data[DOMAIN][config_entry.entry_id][CHILD_LOCKS]
    if async_using_zwave_js(lock=primary_lock):
        entity = ZwaveJSNetworkReadySensor(primary_lock, child_locks)
    elif async_using_ozw(lock=primary_lock):
        entity = OZWNetworkReadySensor(primary_lock, child_locks)
    elif async_using_zwave(lock=primary_lock):
        entity = ZwaveNetworkReadySensor(primary_lock, child_locks)
    else:
        _LOGGER.error("Z-Wave integration not found")
        raise PlatformNotReady

    async_add_entities([entity], True)
    return True


class BaseNetworkReadySensor(BinarySensorEntity):
    """Base binary sensor to indicate whether or not Z-Wave network is ready."""

    def __init__(
        self,
        primary_lock: KeymasterLock,
        child_locks: List[KeymasterLock],
        integration_name: str,
    ) -> None:
        """Initialize sensor."""
        self.primary_lock = primary_lock
        self.child_locks = child_locks
        self.integration_name = integration_name

        self._attr_is_on = False
        self._attr_name = generate_binary_sensor_name(self.primary_lock.lock_name)
        self._attr_unique_id = slugify(self._attr_name)
        self._attr_device_class = DEVICE_CLASS_CONNECTIVITY
        self._attr_should_poll = False

    @callback
    def async_set_is_on_property(
        self, value_to_set: bool, write_state: bool = True
    ) -> None:
        """Update state."""
        # Return immediately if we are not changing state
        if value_to_set == self._attr_is_on:
            return

        if value_to_set:
            _LOGGER.debug("Connected to %s network", self.integration_name)
        else:
            _LOGGER.debug("Disconnected from %s network", self.integration_name)

        self._attr_is_on = value_to_set
        if write_state:
            self.async_write_ha_state()


class ZwaveJSNetworkReadySensor(BaseNetworkReadySensor):
    """Binary sensor to indicate whether or not `zwave_js` network is ready."""

    def __init__(
        self, primary_lock: KeymasterLock, child_locks: List[KeymasterLock]
    ) -> None:
        """Initialize sensor."""
        super().__init__(primary_lock, child_locks, ZWAVE_JS_DOMAIN)
        self.lock_config_entry_id = None
        self._lock_found = True
        self.ent_reg = None
        self._attr_should_poll = True

    async def async_update(self) -> None:
        """Update sensor."""
        if not self.ent_reg:
            self.ent_reg = async_get_entity_registry(self.hass)

        if (
            not self.lock_config_entry_id
            or not self.hass.config_entries.async_get_entry(self.lock_config_entry_id)
        ):
            entity_id = self.primary_lock.lock_entity_id
            lock_ent_reg_entry = self.ent_reg.async_get(entity_id)

            if not lock_ent_reg_entry:
                if self._lock_found:
                    self._lock_found = False
                    _LOGGER.warning("Can't find your lock %s.", entity_id)
                return

            self.lock_config_entry_id = lock_ent_reg_entry.config_entry_id

            if not self._lock_found:
                _LOGGER.info("Found your lock %s", entity_id)
                self._lock_found = True

        try:
            client = self.hass.data[ZWAVE_JS_DOMAIN][self.lock_config_entry_id][
                ZWAVE_JS_DATA_CLIENT
            ]
        except KeyError:
            _LOGGER.debug("Can't access Z-Wave JS data client.")
            self._attr_is_on = False
            return

        network_ready = bool(
            client.connected and client.driver and client.driver.controller
        )

        # If network_ready and self._attr_is_on are both true or both false, we don't need
        # to do anything since there is nothing to update.
        if not network_ready ^ self.is_on:
            return

        self.async_set_is_on_property(network_ready, False)

        # If we just turned the sensor on, we need to get the latest lock
        # nodes and devices
        if self.is_on:
            await async_update_zwave_js_nodes_and_devices(
                self.hass,
                self.lock_config_entry_id,
                self.primary_lock,
                self.child_locks,
            )


class OZWNetworkReadySensor(BaseNetworkReadySensor):
    """Binary sensor to indicate whether or not `ozw` network is ready."""

    def __init__(
        self, primary_lock: KeymasterLock, child_locks: List[KeymasterLock]
    ) -> None:
        """Initialize sensor."""
        super().__init__(primary_lock, child_locks, OZW_DOMAIN)

    @callback
    def async_check_ozw_status(self, msg: models.ReceiveMessage):
        """Check OZW network status."""
        if msg.payload:
            try:
                payload = json.loads(msg.payload).get(OZW_STATUS_KEY)
            except Exception:
                self.async_set_is_on_property(False)
                return

            self.async_set_is_on_property(
                bool(payload and payload in OZW_READY_STATUSES)
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added."""
        self.async_on_remove(
            await async_subscribe(
                self.hass, OZW_STATUS_TOPIC, self.async_check_ozw_status
            )
        )


class ZwaveNetworkReadySensor(BaseNetworkReadySensor):
    """Binary sensor to indicate whether or not `zwave` network is ready."""

    def __init__(
        self, primary_lock: KeymasterLock, child_locks: List[KeymasterLock]
    ) -> None:
        """Initialize sensor."""
        super().__init__(primary_lock, child_locks, ZWAVE_DOMAIN)
        self.network: ZWaveNetwork = None

    @callback
    def async_network_ready_callback(self):
        """Called when network is ready."""
        self.async_set_is_on_property(True)

    @callback
    def async_network_not_ready_callback(self):
        """Called when network is not ready."""
        self.async_set_is_on_property(False)

    @callback
    def async_call_dispatcher(self, dispatcher_func, **kwargs) -> None:
        """Connect/disconnect to/from signals."""
        for signal in ZWAVE_NETWORK_READY_STATUSES:
            dispatcher_func(self.async_network_ready_callback, signal, **kwargs)

        for signal in ZWAVE_NETWORK_NOT_READY_STATUSES:
            dispatcher_func(self.async_network_not_ready_callback, signal, **kwargs)

    async def async_added_to_hass(self) -> None:
        """Run when entity is added."""
        self.network = self.hass.data[ZWAVE_DATA_NETWORK]
        self.async_set_is_on_property(self.network.is_ready)

        self.async_call_dispatcher(dispatcher.connect, weak=False)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is removed."""
        self.async_call_dispatcher(dispatcher.disconnect)
