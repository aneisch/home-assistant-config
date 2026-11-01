"""Support for Lennoxs30 outdoor temperature sensor."""

# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from lennoxs30api import LENNOX_BLE_COMMSTATUS_AVAILABLE, LENNOX_BLE_STATUS_INPUT_AVAILABLE, LennoxBle, lennox_system
from lennoxs30api.lennox_ble import LennoxBleInput

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import UNIQUE_ID_SUFFIX_BLE, UNIQUE_ID_SUFFIX_BLE_COMMSTATUS
from .device import helper_create_ble_device_id
from .helpers import helper_create_system_unique_id

_LOGGER = logging.getLogger(__name__)

DOMAIN = "lennoxs30"


class BleCommStatusBinarySensor(S30BaseEntityMixin, BinarySensorEntity):
    """Entity for S30 connected to internet."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        ble_device: LennoxBle,
    ) -> None:
        """Construct the object."""
        super().__init__(manager, system)
        self._hass = hass
        self._myname = f"{self._system.name} {ble_device.deviceName} comm_status"
        self._ble_device: LennoxBle = ble_device

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass BleCommStatusBinarySensor myname [%s]", self._myname)
        self._ble_device.register_on_update_callback(
            self.update_callback,
            [
                "commStatus",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self) -> None:
        """Process data change."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback BleCommStatusBinarySensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        """Create unique id for entity."""
        return helper_create_system_unique_id(self._system, f"{UNIQUE_ID_SUFFIX_BLE_COMMSTATUS}_{self._ble_device.ble_id}")

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return attributes."""
        return {"commStatus": self._ble_device.commStatus}

    @property
    def name(self) -> str:
        """Return entity name."""
        return self._myname

    @property
    def is_on(self) -> bool:
        """Return state."""
        return self._ble_device.commStatus == LENNOX_BLE_COMMSTATUS_AVAILABLE

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, helper_create_ble_device_id(self._system, self._ble_device))},
        }

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return device_class."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def entity_category(self) -> EntityCategory:
        """Return entity category."""
        return EntityCategory.DIAGNOSTIC


class BleBinarySensor(S30BaseEntityMixin, BinarySensorEntity):
    """Entity for S30 connected to internet."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        ble_device: LennoxBle,
        sensor_value: LennoxBleInput,
        status_value: LennoxBleInput,
        sensor_dict: dict,
    ) -> None:
        """Create the object."""
        super().__init__(manager, system)
        self._hass: HomeAssistant = hass
        self._myname: str = self._system.name + " " + ble_device.deviceName + " " + sensor_dict["name"]
        self._ble_device: LennoxBle = ble_device
        self._sensor_dict: dict = sensor_dict
        self._sensor_value: LennoxBleInput = sensor_value
        self._status_value: LennoxBleInput = status_value
        self._device_class: str = sensor_dict.get("device_class")
        self._entity_category: str = sensor_dict.get("entity_category")

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass BleBinarySensor myname [%s]", self._myname)
        self._ble_device.register_on_update_callback(self.commstatus_update, ["commStatus"])
        self._sensor_value.register_on_update_callback(self.sensor_value_update)
        if self._status_value is not None:
            self._status_value.register_on_update_callback(self.status_value_update)

        await super().async_added_to_hass()

    def commstatus_update(self) -> None:
        """Process data change."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("commstatus_update BleBinarySensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    def sensor_value_update(self) -> None:
        """Process value update."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("sensor_value_update BleBinarySensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    def status_value_update(self) -> None:
        """Process status value."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("status_value_update BleBinarySensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        """Return unique id for entity."""
        return helper_create_system_unique_id(
            self._system,
            f"{UNIQUE_ID_SUFFIX_BLE}_{self._ble_device.ble_id}_{self._sensor_value.input_id}",
        )

    @property
    def name(self) -> str:
        """Return entity name."""
        return self._myname

    @property
    def is_on(self) -> bool:
        """Return on state."""
        return self._sensor_value.value == "1"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, helper_create_ble_device_id(self._system, self._ble_device))},
        }

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return device_class."""
        return self._device_class

    @property
    def available(self) -> bool:
        """Return entity availability."""
        if self._ble_device.commStatus != LENNOX_BLE_COMMSTATUS_AVAILABLE:
            return False
        if self._status_value is not None and self._status_value.value != LENNOX_BLE_STATUS_INPUT_AVAILABLE:
            return False
        return super().available

    @property
    def entity_category(self) -> EntityCategory:
        """Return entity category."""
        return self._entity_category
