"""Support for Lennoxs30 ventilation and allergend defender switches"""
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from lennoxs30api import lennox_system
from lennoxs30api.s30exception import S30Exception

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import (
    LOG_INFO_SWITCH_ASYNC_TURN_OFF,
    LOG_INFO_SWITCH_ASYNC_TURN_ON,
    MANAGER,
    UNIQUE_ID_SUFFIX_PARAMETER_SAFETY_SWITCH,
    VENTILATION_EQUIPMENT_ID,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "lennoxs30"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Setup the switch entities"""
    _LOGGER.debug("switch:async_setup_platform enter")

    switch_list = []
    manager: Manager = hass.data[DOMAIN][entry.unique_id][MANAGER]
    for system in manager.api.system_list:
        _LOGGER.debug("async_setup_platform ventilation [%s]", system.supports_ventilation())
        if system.supports_ventilation():
            _LOGGER.info("Create S30 ventilation switch system [%s]", system.sysId)
            switch = S30VentilationSwitch(hass, manager, system)
            switch_list.append(switch)
        if manager.allergen_defender_switch:
            _LOGGER.info("Create S30 allergenDefender switch system [%s]", system.sysId)
            switch = S30AllergenDefenderSwitch(hass, manager, system)
            switch_list.append(switch)
        if system.numberOfZones > 1:
            _LOGGER.info("Create S30 zoning switch system [%s]", system.sysId)
            switch = S30ZoningSwitch(hass, manager, system)
            switch_list.append(switch)

        ma_switch = S30ManualAwayModeSwitch(hass, manager, system)
        switch_list.append(ma_switch)
        _LOGGER.info("Create S30ManualAwayModeSwitch system [%s]", system.sysId)
        sa_switch = S30SmartAwayEnableSwitch(hass, manager, system)
        switch_list.append(sa_switch)
        _LOGGER.info("Create S30SmartAwayEnableSwitch system [%s]", system.sysId)

        if manager.create_equipment_parameters:
            par_safety_switch = S30ParameterSafetySwitch(hass, manager, system)
            switch_list.append(par_safety_switch)

    if len(switch_list) != 0:
        async_add_entities(switch_list, True)
        _LOGGER.debug("switch:async_setup_platform  created [%d] switch entitites", len(switch_list))
        return True
    return False


class S30VentilationSwitch(S30BaseEntityMixin, SwitchEntity):
    """Class for Lennox S30 thermostat."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_ventilation"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "ventilationRemainingTime",
                "ventilatingUntilTime",
                "diagVentilationRuntime",
                "ventilationMode",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Update callback when data changes"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_VST").replace("-", "")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs: dict[str, Any] = {}
        attrs["ventilationRemainingTime"] = self._system.ventilationRemainingTime
        attrs["ventilatingUntilTime"] = self._system.ventilatingUntilTime
        attrs["diagVentilationRuntime"] = self._system.diagVentilationRuntime
        attrs["alwaysOn"] = self._system.ventilationMode == "on"
        attrs["timed"] = self._system.ventilationRemainingTime != 0
        return attrs

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        return self._system.ventilationMode == "on" or self._system.ventilationRemainingTime > 0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        equip_device_map = self._manager.system_equip_device_map.get(self._system.sysId)
        if equip_device_map is not None:
            device = equip_device_map.get(VENTILATION_EQUIPMENT_ID)
            if device is not None:
                return {
                    "identifiers": {(DOMAIN, device.unique_name)},
                }
            _LOGGER.warning("Unable to find VENTILATION_EQUIPMENT_ID in device map, please raise an issue")
        else:
            _LOGGER.error(
                "No equipment device map found for sysId [%s] equipment VENTILATION_EQUIPMENT_ID, please raise an issue",
                self._system.sysId,
            )
        return {
            "identifiers": {(DOMAIN, self._system.unique_id)},
        }

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        try:
            await self._system.ventilation_on()
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_on [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_on unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        try:
            called = False
            if self._system.ventilationMode == "on":
                _LOGGER.debug("ventilation:async_turn_off calling ventilation_off")
                await self._system.ventilation_off()
                called = True
            if self._system.ventilationRemainingTime > 0:
                await self._system.ventilation_timed(0)
                _LOGGER.debug("ventilation:async_turn_off calling ventilation_timed(0)")
                called = True
            if called:
                self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_off [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_off unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class S30AllergenDefenderSwitch(S30BaseEntityMixin, SwitchEntity):
    """Class for Lennox S30 thermostat."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_allergen_defender"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._system.registerOnUpdateCallback(self.update_callback, ["allergenDefender"])
        await super().async_added_to_hass()

    def update_callback(self):
        """Update callback when data changes"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_ADST").replace("-", "")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {}

    def update(self):
        """Update data from the thermostat API."""
        return True

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        return self._system.allergenDefender

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {"identifiers": {(DOMAIN, self._system.unique_id)}}

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        try:
            await self._system.allergenDefender_on()
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_on [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_on unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        try:
            await self._system.allergenDefender_off()
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_off [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_off unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class S30ManualAwayModeSwitch(S30BaseEntityMixin, SwitchEntity):
    """Class for Lennox S30 thermostat."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_manual_away_mode"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "manualAwayMode",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Update callback when data changes"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_SW_MA").replace("-", "")

    @property
    def extra_state_attributes(self):
        return {}

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        return self._system.get_manual_away_mode()

    @property
    def device_info(self) -> DeviceInfo:
        return {"identifiers": {(DOMAIN, self._system.unique_id)}}

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        try:
            await self._system.set_manual_away_mode(True)
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_on [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_on unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        try:
            await self._system.set_manual_away_mode(False)
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_off [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_off unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class S30SmartAwayEnableSwitch(S30BaseEntityMixin, SwitchEntity):
    """Class for Lennox S30 thermostat."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_smart_away_enable"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "sa_enabled",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Update callback when data changes"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_SW_SAE").replace("-", "")

    @property
    def extra_state_attributes(self):
        return {}

    def update(self):
        return True

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        return self._system.sa_enabled

    @property
    def device_info(self) -> DeviceInfo:
        return {"identifiers": {(DOMAIN, self._system.unique_id)}}

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        try:
            await self._system.enable_smart_away(True)
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_on [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_on unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        try:
            await self._system.enable_smart_away(False)
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_off [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_off unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class S30ZoningSwitch(S30BaseEntityMixin, SwitchEntity):
    """Class for iHarmony Zoning"""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_zoning_enable"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "centralMode",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Update callback when data changes"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("update_callback myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_SW_ZE").replace("-", "")

    @property
    def extra_state_attributes(self):
        return {}

    def update(self):
        return True

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        return self._system.centralMode is False

    @property
    def device_info(self) -> DeviceInfo:
        return {"identifiers": {(DOMAIN, self._system.unique_id)}}

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        try:
            await self._system.centralMode_off()
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_on [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_on unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        try:
            await self._system.centralMode_on()
            self._manager.mp_wakeup_event.set()
        except S30Exception as ex:
            raise HomeAssistantError(f"async_turn_off [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"async_turn_off unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class S30ParameterSafetySwitch(S30BaseEntityMixin, SwitchEntity):
    """S30ParameterSafetySwitch"""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        rearm_duration_sec=60.0,
    ):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_parameter_safety"
        self._rearm_duration_sec = rearm_duration_sec
        self._rearm_task = None
        manager.parameter_safety_turn_on(self._system.sysId)

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (f"{self._system.unique_id}{UNIQUE_ID_SUFFIX_PARAMETER_SAFETY_SWITCH}").replace("-", "")

    @property
    def extra_state_attributes(self):
        return {}

    def update(self):
        return True

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._myname

    @property
    def is_on(self):
        res = self._manager.parameter_safety_on(self._system.sysId)
        return res

    @property
    def device_info(self) -> DeviceInfo:
        return {"identifiers": {(DOMAIN, self._system.unique_id)}}

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_ON, self.__class__.__name__, self._myname)
        self._manager.parameter_safety_turn_on(self._system.sysId)
        if self._rearm_task is not None:
            self._rearm_task.cancel()
            self._rearm_task = None
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(LOG_INFO_SWITCH_ASYNC_TURN_OFF, self.__class__.__name__, self._myname)
        self._manager.parameter_safety_turn_off(self._system.sysId)
        self._rearm_task = asyncio.create_task(self.async_rearm_task())
        self.schedule_update_ha_state()

    async def async_rearm_task(self):
        """Rearms the safety switch"""
        await asyncio.sleep(self._rearm_duration_sec)
        self._manager.parameter_safety_turn_on(self._system.sysId)
        self.schedule_update_ha_state()

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
