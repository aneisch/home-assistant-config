"""Support for Lennoxs30 outdoor temperature sensor"""

# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from lennoxs30api import LennoxBle, lennox_system

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import LENNOX_DOMAIN, UNIQUE_ID_SUFFIX_BLE
from .device import helper_create_ble_device_id
from .helpers import helper_create_system_unique_id

_LOGGER = logging.getLogger(__name__)


class S40IAQSensor(S30BaseEntityMixin, SensorEntity):
    """Class for Lennox S40 BLE Sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        ble_device: LennoxBle,
        sensor_dict: dict,
    ):
        super().__init__(manager, system)
        self._hass: HomeAssistant = hass
        self._ble_device = ble_device
        self._myname: str = self._system.name + " " + ble_device.deviceName + " " + sensor_dict["name"]
        self._sensor_dict: dict = sensor_dict
        self._system_attr: str = sensor_dict["input"]
        self._status_attr: str = sensor_dict.get("status")
        self._uom: str = sensor_dict.get("uom")
        self._state_class: str = sensor_dict.get("state_class")
        self._device_class: str = sensor_dict.get("device_class")
        self._entity_category: str = sensor_dict.get("entity_category")
        self._precision: int = sensor_dict.get("precision", 1)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass S40IAQSensor myname [%s]", self._myname)
        attribs = []
        attribs.append(self._system_attr)
        if self._status_attr is not None:
            attribs.append(self._status_attr)

        self._system.registerOnUpdateCallback(self.sensor_value_update, attribs)
        await super().async_added_to_hass()

    def sensor_value_update(self):
        """Callback to execute on data change"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("sensor_value_update S40IAQSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return helper_create_system_unique_id(
            self._system,
            f"{UNIQUE_ID_SUFFIX_BLE}_{self._ble_device.ble_id}_{self._system_attr}",
        )

    @property
    def name(self):
        return self._myname

    @property
    def native_value(self):
        value = getattr(self._system, self._system_attr)
        if self._state_class is None:
            return value
        try:
            return round(float(value), self._precision)
        except ValueError as e:
            _LOGGER.warning(
                "native_value myname [%s] sensor value [%s] exception: [%s]",
                self._myname,
                value,
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
            "identifiers": {(LENNOX_DOMAIN, helper_create_ble_device_id(self._system, self._ble_device))},
        }

    @property
    def native_unit_of_measurement(self):
        return self._uom

    @property
    def available(self) -> bool:
        if self._status_attr is not None:
            if getattr(self._system, self._status_attr) is not True:
                return False
        return super().available

    @property
    def entity_category(self):
        return self._entity_category
