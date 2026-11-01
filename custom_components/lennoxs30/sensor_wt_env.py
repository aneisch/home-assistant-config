"""Support for Lennoxs30 outdoor temperature sensor"""

# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from lennoxs30api import lennox_system

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import LENNOX_DOMAIN
from .helpers import helper_create_system_unique_id

_LOGGER = logging.getLogger(__name__)


lennox_wt_env_sensors = [
    {
        "name": "wt env airquality",
        "input": "wt_env_airQuality",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env tree",
        "input": "wt_env_tree",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env weed",
        "input": "wt_env_weed",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env grass",
        "input": "wt_env_grass",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env mold",
        "input": "wt_env_mold",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env uv index",
        "input": "wt_env_uvIndex",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
    },
    {
        "name": "wt env humidity",
        "input": "wt_env_humidity",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 0,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.HUMIDITY,
        "uom": PERCENTAGE,
    },
    {
        "name": "wt env cloud coverage",
        "input": "wt_env_cloudCoverage",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 0,
        "state_class": SensorStateClass.MEASUREMENT,
        "uom": PERCENTAGE,
    },
]

lennox_wt_env_sensors_us = [
    {
        "name": "wt env wind speed",
        "input": "wt_env_windSpeed",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.SPEED,
        "uom": UnitOfSpeed.MILES_PER_HOUR,
    },
    {
        "name": "wt env dewpoint",
        "input": "wt_env_dewpoint",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "uom": UnitOfTemperature.FAHRENHEIT,
    },
]

lennox_wt_env_sensors_metric = [
    {
        "name": "wt env wind speed",
        "input": "wt_env_windSpeedK",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.SPEED,
        "uom": UnitOfSpeed.KILOMETERS_PER_HOUR,
    },
    {
        "name": "wt env dewpoint",
        "input": "wt_env_dewpointC",
        "availability_attribute": "wt_is_valid",
        "unavailable_value": "error",
        "precision": 1,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "uom": UnitOfTemperature.CELSIUS,
    },
]


class WTEnvSensor(S30BaseEntityMixin, SensorEntity):
    """Class for Lennox S40 WTEnvSensor Sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        sensor_dict: dict,
    ):
        super().__init__(manager, system)
        self._hass: HomeAssistant = hass
        self._sensor_dict: dict = sensor_dict
        self._myname: str = self._system.name + " " + sensor_dict["name"]
        self._system_attr: str = sensor_dict["input"]
        self._unavailable_value: str = sensor_dict.get("unavailable_value")
        self._availability_attribute: str = sensor_dict.get("availability_attribute")
        self._precision: int = sensor_dict.get("precision")
        self._state_class = sensor_dict.get("state_class")
        self._device_class = sensor_dict.get("device_class")
        self._uom = sensor_dict.get("uom")
        self._entity_category = sensor_dict.get("entity_category")

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass WTEnvSensor myname [%s]", self._myname)
        attribs = []
        attribs.append(self._system_attr)
        if self._availability_attribute is not None:
            attribs.append(self._availability_attribute)
        self._system.registerOnUpdateCallback(self.sensor_value_update, attribs)
        await super().async_added_to_hass()

    def sensor_value_update(self):
        """Callback to execute on data change"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("sensor_value_update WTEnvSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return helper_create_system_unique_id(
            self._system,
            self._system_attr,
        )

    @property
    def name(self):
        return self._myname

    @property
    def native_value(self):
        value = getattr(self._system, self._system_attr)
        if self._state_class is None or value is None:
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
            "identifiers": {(LENNOX_DOMAIN, self._system.unique_id)},
        }

    @property
    def native_unit_of_measurement(self):
        return self._uom

    @property
    def available(self) -> bool:
        attr_val = getattr(self._system, self._system_attr)
        if attr_val is None or attr_val == self._unavailable_value:
            return False
        attr_avail = getattr(self._system, self._availability_attribute)
        if attr_avail is None or attr_avail is False:
            return False
        return super().available

    @property
    def entity_category(self):
        return self._entity_category
