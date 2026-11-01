"""Support for Lennoxs30 outdoor temperature sensor"""

# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
import logging

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from lennoxs30api import (
    LENNOX_BLE_COMMSTATUS_AVAILABLE,
    LENNOX_BLE_STATUS_INPUT_AVAILABLE,
    LennoxBle,
    lennox_system,
)
from lennoxs30api.lennox_ble import LennoxBleInput

from . import DOMAIN, Manager
from .base_entity import S30BaseEntityMixin
from .const import (
    UNIQUE_ID_SUFFIX_BLE,
)
from .device import helper_create_ble_device_id
from .helpers import (
    helper_create_system_unique_id,
    lennox_uom_to_ha_uom,
)

_LOGGER = logging.getLogger(__name__)


class S40BleSensor(S30BaseEntityMixin, SensorEntity):
    """Class for Lennox S40 BLE Sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        ble_device: LennoxBle,
        sensor_value: LennoxBleInput,
        status_value: LennoxBleInput,
        sensor_dict: dict,
    ):
        super().__init__(manager, system)
        self._hass: HomeAssistant = hass
        self._myname: str = self._system.name + " " + ble_device.deviceName + " " + sensor_dict["name"]
        self._ble_device: LennoxBle = ble_device
        self._sensor_dict: dict = sensor_dict
        self._sensor_value: LennoxBleInput = sensor_value
        self._status_value: LennoxBleInput = status_value
        self._uom: str = sensor_dict.get("uom", lennox_uom_to_ha_uom(sensor_value.unit))
        self._state_class: str = sensor_dict.get("state_class")
        self._device_class: str = sensor_dict.get("device_class")
        self._entity_category: str = sensor_dict.get("entity_category")

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass S40BleSensor myname [%s]", self._myname)
        self._ble_device.register_on_update_callback(self.commstatus_update, ["commStatus"])
        self._sensor_value.register_on_update_callback(self.sensor_value_update)
        if self._status_value is not None:
            self._status_value.register_on_update_callback(self.status_value_update)

        await super().async_added_to_hass()

    def commstatus_update(self):
        """Callback to execute on data change"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("commstatus_update S40BleSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    def sensor_value_update(self):
        """Callback to execute on data change"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("sensor_value_update S40BleSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    def status_value_update(self):
        """Callback to execute on data change"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("status_value_update S40BleSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return helper_create_system_unique_id(
            self._system,
            f"{UNIQUE_ID_SUFFIX_BLE}_{self._ble_device.ble_id}_{self._sensor_value.input_id}",
        )

    @property
    def name(self):
        return self._myname

    @property
    def native_value(self):
        try:
            return round(float(self._sensor_value.value), 1)
        except ValueError as e:
            _LOGGER.warning(
                "native_value myname [%s] sensor value [%s] exception: [%s]",
                self._myname,
                self._sensor_value.value,
                e,
            )
        return None

    @property
    def state_class(self):
        return self._state_class

    @property
    def device_class(self):
        return self._device_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, helper_create_ble_device_id(self._system, self._ble_device))},
        }

    @property
    def native_unit_of_measurement(self):
        return self._uom

    @property
    def available(self) -> bool:
        if self._ble_device.commStatus != LENNOX_BLE_COMMSTATUS_AVAILABLE:
            return False
        if self._status_value is not None:
            if self._status_value.value != LENNOX_BLE_STATUS_INPUT_AVAILABLE:
                return False
        return super().available

    @property
    def entity_category(self):
        return self._entity_category
