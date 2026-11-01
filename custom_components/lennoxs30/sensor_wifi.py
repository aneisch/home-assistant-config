"""Support for Lennoxs30 outdoor temperature sensor"""

# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from lennoxs30api import lennox_system

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import LENNOX_DOMAIN, UNIQUE_ID_SUFFIX_WIFI_RSSI

_LOGGER = logging.getLogger(__name__)


class WifiRSSISensor(S30BaseEntityMixin, SensorEntity):
    """Class for Lennox S40 WTEnvSensor Sensors."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_wifi_rssi"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass WifiRSSISensor myname [%s]", self._myname)
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "wifi_rssi",
                "wifi_macAddr",
                "wifi_ssid",
                "wifi_ip",
                "wifi_router",
                "wifi_dns",
                "wifi_dns2",
                "wifi_subnetMask",
                "wifi_bitRate",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Callback to execute on data change"""
        _LOGGER.debug("update_callback WifiRSSISensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return (self._system.unique_id + UNIQUE_ID_SUFFIX_WIFI_RSSI).replace("-", "")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs: dict[str, Any] = {}
        attrs["macAddr"] = self._system.wifi_macAddr
        attrs["ssid"] = self._system.wifi_ssid
        attrs["ip"] = self._system.wifi_ip
        attrs["router"] = self._system.wifi_router
        attrs["dns"] = self._system.wifi_dns
        attrs["dns2"] = self._system.wifi_dns2
        attrs["subnetMask"] = self._system.wifi_subnetMask
        attrs["bitRate"] = self._system.wifi_bitRate
        return attrs

    @property
    def name(self):
        return self._myname

    @property
    def native_value(self):
        return self._system.wifi_rssi

    @property
    def native_unit_of_measurement(self):
        return SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    @property
    def device_class(self):
        return SensorDeviceClass.SIGNAL_STRENGTH

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(LENNOX_DOMAIN, self._system.unique_id)},
        }

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC
