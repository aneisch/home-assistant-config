"""Support for Lennoxs30 outdoor temperature sensor."""
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform as ep
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from lennoxs30api import (
    LENNOX_CIRCULATE_TIME_MAX,
    LENNOX_CIRCULATE_TIME_MIN,
    lennox_system,
    lennox_zone,
)
from lennoxs30api.lennox_equipment import (
    LENNOX_EQUIPMENT_PARAMETER_FORMAT_RANGE,
    lennox_equipment,
    lennox_equipment_parameter,
)
from lennoxs30api.s30exception import S30Exception

from . import DOMAIN, Manager
from .base_entity import S30BaseEntityMixin
from .const import (
    LOG_INFO_NUMBER_ASYNC_SET_VALUE,
    MANAGER,
    UNIQUE_ID_SUFFIX_DEHUM_SETPOINT,
    UNIQUE_ID_SUFFIX_EQ_PARAM_NUMBER,
    UNIQUE_ID_SUFFIX_HUM_SETPOINT,
    UNIQUE_ID_SUFFIX_TIMED_VENTILATION_NUMBER,
    VENTILATION_EQUIPMENT_ID,
)
from .helpers import (
    helper_create_equipment_entity_name,
    helper_get_equipment_device_info,
    helper_get_parameter_extra_attributes,
    lennox_uom_to_ha_uom,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities"""
    _LOGGER.debug("number:async_setup_platform enter")
    number_list = []
    manager: Manager = hass.data[DOMAIN][entry.unique_id][MANAGER]

    if manager.create_equipment_parameters:
        platform = ep.async_get_current_platform()
        platform.async_register_entity_service(
            "set_zonetest_parameter",
            {
                vol.Required("value"): cv.positive_float,
                vol.Required("enabled"): cv.boolean,
            },
            "async_set_zonetest_parameter",
        )

    for system in manager.api.system_list:
        # We do not support setting diag level from a cloud connection
        if manager.api.isLANConnection is False or (manager.create_inverter_power is False and manager.create_diagnostic_sensors is False):
            _LOGGER.debug("async_setup_entry - not creating diagnostic level number because inverter power and diagnostics not enabled")
        else:
            number = DiagnosticLevelNumber(hass, manager, system)
            number_list.append(number)
        if system.enhancedDehumidificationOvercoolingF_enable and system.is_none(system.dehumidifierType) is False:
            number = DehumidificationOverCooling(hass, manager, system)
            number_list.append(number)
        number = CirculateTime(hass, manager, system)
        number_list.append(number)

        if system.supports_ventilation():
            number = TimedVentilationNumber(hass, manager, system)
            number_list.append(number)

        if manager.create_equipment_parameters:
            for equipment in system.equipment.values():
                for parameter in equipment.parameters.values():
                    if parameter.enabled and parameter.descriptor == LENNOX_EQUIPMENT_PARAMETER_FORMAT_RANGE:
                        number = EquipmentParameterNumber(hass, manager, system, equipment, parameter)
                        number_list.append(number)

        for zone in system.zone_list:
            if zone.humidificationOption:
                number = HumidifySetpointNumber(hass, manager, system, zone)
                number_list.append(number)
            if zone.dehumidificationOption:
                number = DehumidifySetpointNumber(hass, manager, system, zone)
                number_list.append(number)

    if len(number_list) != 0:
        async_add_entities(number_list, True)


class DiagnosticLevelNumber(S30BaseEntityMixin, NumberEntity):
    """Set the diagnostic level in the S30."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_diagnostic_level"
        _LOGGER.debug("Create DiagnosticLevelNumber myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass DiagnosticLevelNumber myname [%s]", self._myname)
        self._system.registerOnUpdateCallback(self.update_callback, ["diagLevel"])
        await super().async_added_to_hass()

    def update_callback(self):
        """Called when state has changed"""
        _LOGGER.debug("update_callback DiagnosticLevelNumber myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_DL").replace("-", "")

    @property
    def name(self):
        return self._myname

    @property
    def native_max_value(self) -> float:
        return 2

    @property
    def native_min_value(self) -> float:
        return 0

    @property
    def native_step(self) -> float:
        return 1

    @property
    def native_value(self) -> float:
        return self._system.diagLevel

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)
        try:
            if value == 1:
                _LOGGER.warning(
                    "Diagnostic Level Number - setting to a value of 1 is not recommeded. See https://github.com/PeteRager/lennoxs30/blob/master/docs/diagnostics.md"
                )
            if value != 0 and (self._system.internetStatus or self._system.relayServerConnected):
                _LOGGER.warning(
                    "Diagnostic Level Number - setting to a non-zero value is not recommended for systems connected to the lennox cloud internetStatus [%s] relayServerConnected [%s] - https://github.com/PeteRager/lennoxs30/blob/master/docs/diagnostics.md",
                    self._system.internetStatus,
                    self._system.relayServerConnected,
                )
            await self._system.set_diagnostic_level(value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        result = {
            "identifiers": {(DOMAIN, self._system.unique_id)},
        }
        return result


class DehumidificationOverCooling(S30BaseEntityMixin, NumberEntity):
    """Set the diagnostic level in the S30."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_dehumidification_overcooling"
        _LOGGER.debug("Create DehumidificationOverCooling myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass DehumidificationOverCooling myname [%s]", self._myname)
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "enhancedDehumidificationOvercoolingC_enable",
                "enhancedDehumidificationOvercoolingF_enable",
                "enhancedDehumidificationOvercoolingC",
                "enhancedDehumidificationOvercoolingF",
                "enhancedDehumidificationOvercoolingF_min",
                "enhancedDehumidificationOvercoolingF_max",
                "enhancedDehumidificationOvercoolingF_inc",
                "enhancedDehumidificationOvercoolingC_min",
                "enhancedDehumidificationOvercoolingC_max",
                "enhancedDehumidificationOvercoolingC_inc",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Called when state has changed"""
        _LOGGER.debug("update_callback DehumidificationOverCooling myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_DOC").replace("-", "")

    @property
    def name(self):
        return self._myname

    @property
    def native_unit_of_measurement(self):
        if self._manager.is_metric is False:
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def native_max_value(self) -> float:
        if self._manager.is_metric:
            return self._system.enhancedDehumidificationOvercoolingC_max
        return self._system.enhancedDehumidificationOvercoolingF_max

    @property
    def native_min_value(self) -> float:
        if self._manager.is_metric:
            return self._system.enhancedDehumidificationOvercoolingC_min
        return self._system.enhancedDehumidificationOvercoolingF_min

    @property
    def native_step(self) -> float:
        if self._manager.is_metric:
            return self._system.enhancedDehumidificationOvercoolingC_inc
        return self._system.enhancedDehumidificationOvercoolingF_inc

    @property
    def native_value(self) -> float:
        if self._manager.is_metric:
            return self._system.enhancedDehumidificationOvercoolingC
        return self._system.enhancedDehumidificationOvercoolingF

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)
        try:
            if self._manager.is_metric:
                await self._system.set_enhancedDehumidificationOvercooling(r_c=value)
            else:
                await self._system.set_enhancedDehumidificationOvercooling(r_f=value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        result = {
            "identifiers": {(DOMAIN, self._system.unique_id)},
        }
        return result


class CirculateTime(S30BaseEntityMixin, NumberEntity):
    """Set the diagnostic level in the S30."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_circulate_time"
        _LOGGER.debug("Create CirculateTime myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass CirculateTime myname [%s]", self._myname)
        self._system.registerOnUpdateCallback(
            self.update_callback,
            [
                "circulateTime",
            ],
        )
        await super().async_added_to_hass()

    def update_callback(self):
        """Called when state has changed"""
        _LOGGER.debug("update_callback CirculateTime myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + "_CIRC_TIME").replace("-", "")

    @property
    def name(self):
        return self._myname

    @property
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @property
    def native_max_value(self) -> float:
        return LENNOX_CIRCULATE_TIME_MAX

    @property
    def native_min_value(self) -> float:
        return LENNOX_CIRCULATE_TIME_MIN

    @property
    def native_step(self) -> float:
        return 1.0

    @property
    def native_value(self) -> float:
        return self._system.circulateTime

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)

        try:
            await self._system.set_circulateTime(value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        result = {
            "identifiers": {(DOMAIN, self._system.unique_id)},
        }
        return result


class TimedVentilationNumber(S30BaseEntityMixin, NumberEntity):
    """Set timed ventilation."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system):
        super().__init__(manager, system)
        self._hass = hass
        self._myname = self._system.name + "_ventilate_now"
        _LOGGER.debug("Create TimedVentilationNumber myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass TimedVentilationNumber myname [%s]", self._myname)
        self._system.registerOnUpdateCallback(self.update_callback, ["ventilationRemainingTime"])
        await super().async_added_to_hass()

    def update_callback(self):
        """Called when state has changed"""
        _LOGGER.debug("update_callback TimedVentilationNumber myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (self._system.unique_id + UNIQUE_ID_SUFFIX_TIMED_VENTILATION_NUMBER).replace("-", "")

    @property
    def name(self):
        return self._myname

    @property
    def native_max_value(self) -> float:
        return 1440

    @property
    def native_min_value(self) -> float:
        return 0

    @property
    def native_step(self) -> float:
        return 1

    @property
    def native_value(self) -> float:
        return int(self._system.ventilationRemainingTime / 60)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)

        try:
            value_i = int(value)
            value_seconds = value_i * 60
            await self._system.ventilation_timed(value_seconds)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except ValueError as v:
            raise HomeAssistantError(f"TimedVentilationNumber::async_set_native_value invalid value [{value}] ValueError [{v}]") from v
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    @property
    def native_unit_of_measurement(self):
        return UnitOfTime.MINUTES

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return helper_get_equipment_device_info(self._manager, self._system, VENTILATION_EQUIPMENT_ID)


class EquipmentParameterNumber(S30BaseEntityMixin, NumberEntity):
    """Set timed ventilation."""

    # These parameters are absolute temperatures and will be given a device class.
    absolute_temperature_pids: list[int] = [
        202,
        203,
        105,
        106,
        128,
        129,
        55,
        178,
        194,
        195,
        179,
        297,
        298,
        299,
        300,
        301,
        302,
        326,
        327,
        328,
    ]

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
        system: lennox_system,
        equipment: lennox_equipment,
        parameter: lennox_equipment_parameter,
    ):
        super().__init__(manager, system)
        self._hass = hass
        self.equipment = equipment
        self.parameter = parameter

        self._myname = helper_create_equipment_entity_name(system, equipment, parameter.name, prefix="par")
        _LOGGER.debug(
            "Create EquipmentParameterNumber eq [%d] pid [%d] myname [%s]",
            equipment.equipment_id,
            parameter.pid,
            self._myname,
        )
        self._attr_native_unit_of_measurement = lennox_uom_to_ha_uom(self.parameter.unit)
        self._attr_device_class = self._get_device_class()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug(
            "async_added_to_hass EquipmentParameterNumber eq [%d] pid [%d]  myname [%s]",
            self.equipment.equipment_id,
            self.parameter.pid,
            self._myname,
        )
        self._system.registerOnUpdateCallbackEqParameters(
            self.update_callback,
            [f"{self.equipment.equipment_id}_{self.parameter.pid}"],
        )
        await super().async_added_to_hass()

    def update_callback(self, pid: str):
        """Called when state has changed"""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "update_callback EquipmentParameterNumber myname [%s] [%s] [%s]",
                self._myname,
                pid,
                self.parameter.value,
            )
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        # HA fails with dashes in IDs
        return (f"{self._system.unique_id}_{UNIQUE_ID_SUFFIX_EQ_PARAM_NUMBER}_{self.equipment.equipment_id}_{self.parameter.pid}").replace(
            "-", ""
        )

    @property
    def name(self):
        return self._myname

    @property
    def native_max_value(self) -> float:
        return float(self.parameter.range_max)

    @property
    def native_min_value(self) -> float:
        return float(self.parameter.range_min)

    @property
    def native_step(self) -> float:
        return float(self.parameter.range_inc)

    @property
    def native_value(self) -> float:
        return float(self.parameter.value)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)

        if self._manager.parameter_safety_on(self._system.sysId):
            raise HomeAssistantError(f"Unable to set parameter [{self._myname}] parameter safety switch is on")

        try:
            await self._system.set_equipment_parameter_value(self.equipment.equipment_id, self.parameter.pid, value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex

    def _get_device_class(self) -> NumberDeviceClass | None:
        uom = self._attr_native_unit_of_measurement
        if uom in (UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT):
            # Many of the parameters are temperature offsets, for now we only
            # report absolute temperatures as having the device_class which allows
            # then to be automatically translated to celsius
            if self.parameter.pid in self.absolute_temperature_pids:
                return NumberDeviceClass.TEMPERATURE
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return helper_get_equipment_device_info(self._manager, self._system, self.equipment.equipment_id)

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def mode(self):
        return "box"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return helper_get_parameter_extra_attributes(self.equipment, self.parameter)

    async def async_set_zonetest_parameter(self, value: float, enabled: bool):
        """Async function for setting zone test parameters"""
        _LOGGER.info(
            "EquipmentParameterNumber::async_set_zonetest_parameter [%s] set value to [%f] enabled [%s] equipment_id [%d] pid [%s]",
            self._myname,
            value,
            enabled,
            self.equipment.equipment_id,
            self.equipment.equipment_id,
        )

        if self.equipment.equipment_id != 0:
            raise HomeAssistantError(
                f"EquipmentParameterNumber::async_set_zonetest_parameter invalid equipment for zoneTest [{self._myname}] set value to [{value}] equipment_id [{self.equipment.equipment_id}]"
            )
        try:
            await self._system.set_zone_test_parameter_value(self.parameter.pid, value, enabled)
        except S30Exception as ex:
            raise HomeAssistantError(f"async_set_zonetest_parameter [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(
                f"async_set_zonetest_parameter unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            ) from ex


class HumidifySetpointNumber(S30BaseEntityMixin, NumberEntity):
    """Set the diagnostic level in the S30."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system, zone: lennox_zone) -> None:
        super().__init__(manager, system)
        self._hass = hass
        self._zone = zone
        self._myname = f"{system.name}_{zone.name}_hum_setpoint"
        self._attr_name = self._myname
        self._attr_unique_id = (zone.unique_id + UNIQUE_ID_SUFFIX_HUM_SETPOINT).replace("-", "")
        self._attr_device_class = NumberDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_step = 1
        self._attr_device_info = {
            "identifiers": {(DOMAIN, zone.unique_id)},
        }
        _LOGGER.debug("Create HumidifySetpointNumber myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass HumidifySetpointNumber myname [%s]", self._myname)
        self._zone.registerOnUpdateCallback(self.update_callback)
        await super().async_added_to_hass()

    def update_callback(self) -> None:
        """State has changed."""
        _LOGGER.debug("update_callback HumidifySetpointNumber myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def native_max_value(self) -> float:
        return self._zone.maxHumSp

    @property
    def native_min_value(self) -> float:
        return self._zone.minHumSp

    @property
    def native_value(self) -> float:
        return self._zone.husp

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)
        try:
            await self._zone.perform_humidify_setpoint(r_husp=value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex


class DehumidifySetpointNumber(S30BaseEntityMixin, NumberEntity):
    """Set the diagnostic level in the S30."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system, zone: lennox_zone) -> None:
        super().__init__(manager, system)
        self._hass = hass
        self._zone = zone
        self._myname = f"{system.name}_{zone.name}_dehum_setpoint"
        self._attr_name = self._myname
        self._attr_unique_id = (zone.unique_id + UNIQUE_ID_SUFFIX_DEHUM_SETPOINT).replace("-", "")
        self._attr_device_class = NumberDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_step = 1
        self._attr_device_info = {
            "identifiers": {(DOMAIN, zone.unique_id)},
        }
        _LOGGER.debug("Create DehumidifySetpointNumber myname [%s]", self._myname)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass DehumidifySetpointNumber myname [%s]", self._myname)
        self._zone.registerOnUpdateCallback(self.update_callback)
        await super().async_added_to_hass()

    def update_callback(self) -> None:
        """Called when state has changed."""
        _LOGGER.debug("update_callback DehumidifySetpointNumber myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def native_max_value(self) -> float:
        return self._zone.maxDehumSp

    @property
    def native_min_value(self) -> float:
        return self._zone.minDehumSp

    @property
    def native_value(self) -> float:
        return self._zone.desp

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(LOG_INFO_NUMBER_ASYNC_SET_VALUE, self.__class__.__name__, self._myname, value)
        try:
            await self._zone.perform_humidify_setpoint(r_desp=value)
        except S30Exception as ex:
            raise HomeAssistantError(f"set_native_value [{self._myname}] [{ex.as_string()}]") from ex
        except Exception as ex:
            raise HomeAssistantError(f"set_native_value unexpected exception, please log issue, [{self._myname}] exception [{ex}]") from ex
