"""Support for Lennoxs30 Climate Entity."""
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=abstract-method

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_OFF,
    FAN_ON,
    PRESET_AWAY,
    PRESET_NONE,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from lennoxs30api import (
    EC_BAD_PARAMETERS,
    LENNOX_BAD_STATUS,
    LENNOX_HUMID_OPERATION_DEHUMID,
    LENNOX_HUMID_OPERATION_WAITING,
    LENNOX_HUMIDITY_MODE_DEHUMIDIFY,
    LENNOX_HUMIDITY_MODE_HUMIDIFY,
    LENNOX_HVAC_HEAT_COOL,
    LENNOX_TEMP_OPERATION_OFF,
    S30Exception,
    lennox_system,
    lennox_zone,
)
from lennoxs30api.s30api_async import (
    LENNOX_HVAC_COOL,
    LENNOX_HVAC_EMERGENCY_HEAT,
    LENNOX_HVAC_HEAT,
    LENNOX_HVAC_OFF,
    LENNOX_MANUAL_MODE_SCHEDULE_START_INDEX,
)

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import MANAGER

_LOGGER = logging.getLogger(__name__)

# HA doesn't have a 'circulate' state defined for fan.
FAN_CIRCULATE = "circulate"
# Additional Presets
PRESET_CANCEL_HOLD = "cancel hold"
PRESET_CANCEL_AWAY_MODE = "cancel away mode"
PRESET_SCHEDULE_OVERRIDE = "schedule hold"
# Basic set of support flags for every HVAC setup
SUPPORT_FLAGS = ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.TURN_OFF
# Standard set of fan modes
FAN_MODES = [FAN_AUTO, FAN_ON, FAN_CIRCULATE]

DOMAIN = "lennoxs30"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Set up the climate entity."""
    _LOGGER.debug("climate:async_setup_platform enter")
    climate_list = []
    manager: Manager = hass.data[DOMAIN][entry.unique_id][MANAGER]
    for system in manager.api.system_list:
        for zone in system.zone_list:
            if zone.is_zone_active():
                _LOGGER.debug(
                    "Create S30 Climate system [%s] zone [%s]  metric [%s]",
                    system.sysId,
                    zone.name,
                    manager.is_metric,
                )
                climate = S30Climate(hass, manager, system, zone)
                climate_list.append(climate)
            else:
                _LOGGER.debug("Skipping inactive zone - system [%s] zone [%s]", system.sysId, zone.name)
    if len(climate_list) != 0:
        async_add_entities(climate_list, update_before_add=True)
        _LOGGER.debug("climate:async_setup_platform exit - created [%d] entitites", len(climate_list))
    else:
        _LOGGER.error("climate:async_setup_platform exit - no climate entities found")
    return True


class S30Climate(S30BaseEntityMixin, ClimateEntity):
    """Class for Lennox S30 thermostat."""

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system, zone: lennox_zone) -> None:
        """Initialize the climate device."""
        super().__init__(manager, system)
        self.hass: HomeAssistant = hass
        self._zone = zone
        self._myname = self._system.name + "_" + self._zone.name
        self._enable_turn_on_off_backwards_compatibility = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass S30Climate myname [%s]", self._myname)
        self._zone.registerOnUpdateCallback(self.zone_update_callback)
        # We need notification of state of system.manualAwayMode in order to update the preset mode in HA.
        self._system.registerOnUpdateCallback(
            self.system_update_callback,
            [
                "manualAwayMode",
                "sa_enabled",
                "sa_state",
                "sa_reset",
                "sa_cancel",
                "sa_setpointState",
                "zoningMode",
            ],
        )
        await super().async_added_to_hass()

    @property
    def unique_id(self) -> str:
        """Returns unique identifier for this entity."""
        return self._zone.unique_id

    def zone_update_callback(self) -> None:
        """Trigger Callbacks for zone changes that affect this entity."""
        self.schedule_update_ha_state()

    def system_update_callback(self) -> None:
        """Trigger Callbacks for system changes that affect this entity."""
        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs: dict[str, Any] = {}
        attrs["allergenDefender"] = self._zone.allergenDefender if self.is_zone_enabled else None
        attrs["damper"] = self._zone.damper if self.is_zone_enabled else None
        attrs["demand"] = self._zone.demand if self.is_zone_enabled else None
        if self.is_zone_enabled:
            if self._zone.fan:
                attrs["fan"] = FAN_ON
            else:
                attrs["fan"] = FAN_OFF
        else:
            attrs["fan"] = None
        attrs["humidityMode"] = self._zone.humidityMode if self.is_zone_enabled else None
        attrs["humOperation"] = self._zone.humOperation if self.is_zone_enabled else None
        attrs["tempOperation"] = self._zone.tempOperation if self.is_zone_enabled else None
        attrs["ventilation"] = self._zone.ventilation if self.is_zone_enabled else None
        attrs["heatCoast"] = self._zone.heatCoast if self.is_zone_enabled else None
        attrs["defrost"] = self._zone.defrost if self.is_zone_enabled else None
        attrs["balancePoint"] = self._zone.balancePoint if self.is_zone_enabled else None
        attrs["aux"] = self._zone.aux if self.is_zone_enabled else None
        attrs["coolCoast"] = self._zone.coolCoast if self.is_zone_enabled else None
        attrs["ssr"] = self._zone.ssr if self.is_zone_enabled else None
        attrs["zoneEnabled"] = self.is_zone_enabled
        attrs["zoningMode"] = self._system.zoningMode
        return attrs

    @property
    def name(self) -> str:
        """Returns the name."""
        return self._myname

    @property
    def is_zone_disabled(self) -> bool:
        """Determine if the zone is disabled."""
        return self._zone.is_zone_disabled

    @property
    def is_zone_enabled(self) -> bool:
        """Determine if the zone is enabled."""
        # When zoning is disabled, only zone 0 is enabled
        return not self._zone.is_zone_disabled

    def is_single_setpoint_active(self) -> bool:
        """Determine if there are one or two setpoints active."""
        # If the system is configured to use a single setpoint for both heat and cool
        if self._zone.system.single_setpoint_mode:
            return True
        # If it's in heat and cool then there are two setpoints
        return self._zone.systemMode != LENNOX_HVAC_HEAT_COOL

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        mask: ClimateEntityFeature = ClimateEntityFeature(0)
        if not self.is_zone_disabled:
            mask = SUPPORT_FLAGS

            # Target temperature.
            # If its a cooling or heating only system, then there is only one setpoint
            if self.is_single_setpoint_active():
                mask |= ClimateEntityFeature.TARGET_TEMPERATURE
            else:
                mask |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

            if (self._zone.humidificationOption or self._zone.dehumidificationOption) and (
                self._zone.humidityMode in [LENNOX_HUMIDITY_MODE_DEHUMIDIFY, LENNOX_HUMIDITY_MODE_HUMIDIFY]
            ):
                mask |= ClimateEntityFeature.TARGET_HUMIDITY

        _LOGGER.debug("climate:supported_features name [%s] support_flags [%d]", self._myname, SUPPORT_FLAGS)
        return mask

    @property
    def temperature_unit(self) -> UnitOfTemperature:
        """Return the unit of measurement."""
        if self._manager.is_metric is False:
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def _min_heat_cool_temp(self) -> float:
        if self._system.single_setpoint_mode:
            if self._manager.is_metric is False:
                return self._zone.minCsp
            return self._zone.minCspC
        if self._manager.is_metric is False:
            return self._zone.minHsp
        return self._zone.minHspC

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self._zone.systemMode == LENNOX_HVAC_OFF or self._zone.systemMode is None or self.is_zone_disabled:
            return self._min_heat_cool_temp
        if self._zone.systemMode == LENNOX_HVAC_COOL:
            if self._manager.is_metric is False:
                return self._zone.minCsp
            return self._zone.minCspC
        if self._zone.systemMode in [LENNOX_HVAC_HEAT, LENNOX_HVAC_EMERGENCY_HEAT]:
            if self._manager.is_metric is False:
                return self._zone.minHsp
            return self._zone.minHspC
        if self._zone.systemMode == LENNOX_HVAC_HEAT_COOL:
            return self._min_heat_cool_temp
        _LOGGER.warning("min_temp - unexpected system mode [%s] returning default - please raise an issue", self._zone.systemMode)
        return super().min_temp

    @property
    def _max_heat_cool_temp(self) -> float:
        if self._system.single_setpoint_mode:
            if self._manager.is_metric is False:
                return self._zone.maxHsp
            return self._zone.maxHspC
        if self._manager.is_metric is False:
            return self._zone.maxCsp
        return self._zone.maxCspC

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._zone.systemMode == LENNOX_HVAC_OFF or self._zone.systemMode is None or self.is_zone_disabled:
            return self._max_heat_cool_temp
        if self._zone.systemMode == LENNOX_HVAC_COOL:
            if self._manager.is_metric is False:
                return self._zone.maxCsp
            return self._zone.maxCspC
        if self._zone.systemMode in [LENNOX_HVAC_HEAT, LENNOX_HVAC_EMERGENCY_HEAT]:
            if self._manager.is_metric is False:
                return self._zone.maxHsp
            return self._zone.maxHspC
        if self._zone.systemMode == LENNOX_HVAC_HEAT_COOL:
            return self._max_heat_cool_temp
        _LOGGER.warning("max_temp - unexpected system mode [%s] returning default - please raise an issue", self._zone.systemMode)
        return super().max_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self.is_zone_disabled:
            return None

        if self._manager.is_metric is False:
            return self._zone.getTargetTemperatureF()
        return self._zone.getTargetTemperatureC()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._zone.temperatureStatus in LENNOX_BAD_STATUS:
            _LOGGER.warning(
                "climate:current_temperature name [%s] has bad data quality - temperatureStatus [%s] returning None",
                self._myname,
                self._zone.temperatureStatus,
            )
            return None
        if self._manager.is_metric is False:
            t = self._zone.getTemperature()
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("climate:current_temperature name [%s] temperature [%s] F", self._myname, t)
        else:
            t = self._zone.getTemperatureC()
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("climate:current_temperature name [%s] temperature [%s] C", self._myname, t)
        return t

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        if self.is_zone_disabled:
            return None
        if self.is_single_setpoint_active():
            return None
        if self._manager.is_metric is False:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("climate:target_temperature_high name [%s] temperature [%s] F", self._myname, self._zone.csp)
            return self._zone.csp
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("climate:target_temperature_high name [%s] temperature [%s] C", self._myname, self._zone.cspC)
        return self._zone.cspC

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        if self.is_zone_disabled:
            return None
        if self.is_single_setpoint_active():
            return None
        if self._manager.is_metric is False:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("climate:target_temperature_low name [%s] temperature [%s] F", self._myname, self._zone.hsp)
            return self._zone.hsp
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("climate:target_temperature_low name [%s] temperature [%s] C", self._myname, self._zone.hspC)
        return self._zone.hspC

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity."""
        if self._zone.humidityStatus in LENNOX_BAD_STATUS:
            _LOGGER.warning(
                "climate:current_humidity name [%s] has bad data quality - humidityStatus [%s] returning None",
                self._myname,
                self._zone.humidityStatus,
            )
            return None
        h = self._zone.getHumidity()
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("climate:current_humidity name [%s] humidity [%s]", self._myname, h)
        return h

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current hvac operation mode."""
        r = self._zone.getSystemMode()
        if r == LENNOX_HVAC_HEAT_COOL:
            r = HVACMode.HEAT_COOL
        elif r == LENNOX_HVAC_EMERGENCY_HEAT:
            r = HVACMode.HEAT
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("climate:hvac_mode name [%s] mode [%s]", self._myname, r)
        return r

    @property
    def target_temperature_step(self) -> float:
        """Return the step size for setting temperatures."""
        if self._manager.is_metric is False:
            return 1.0
        return 0.5

    @property
    def max_humidity(self) -> float | None:
        """Maximum humidity."""
        if self.is_zone_disabled:
            return None
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_DEHUMIDIFY:
            return self._zone.maxDehumSp
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_HUMIDIFY:
            return self._zone.maxHumSp
        return None

    @property
    def min_humidity(self) -> float | None:
        """Minimum humidity."""
        if self.is_zone_disabled:
            return None
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_DEHUMIDIFY:
            return self._zone.minDehumSp
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_HUMIDIFY:
            return self._zone.minHumSp
        return None

    @property
    def target_humidity(self) -> float:
        """Target humidity."""
        if self.is_zone_disabled:
            return None
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_DEHUMIDIFY:
            return self._zone.desp
        if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_HUMIDIFY:
            return self._zone.husp
        return None

    async def async_set_humidity(self, humidity: float) -> None:
        """Set new target humidity."""
        _LOGGER.info("climate:async_set_humidity zone [%s] humidity [%s]", self._myname, humidity)
        if self.is_zone_disabled:
            err = f"Unable to set humidity as zone [{self._myname}] is disabled"
            raise HomeAssistantError(err)
        if self._zone.humidityMode not in (LENNOX_HUMIDITY_MODE_DEHUMIDIFY, LENNOX_HUMIDITY_MODE_HUMIDIFY):
            err = f"Unable to set humidity as humidity mode is [{self._zone.humidityMode}] on zone [{self._myname}]"
            raise HomeAssistantError(err)
        try:
            if self._zone.humidityMode == LENNOX_HUMIDITY_MODE_DEHUMIDIFY:
                await self._zone.perform_humidify_setpoint(r_desp=humidity)
            elif self._zone.humidityMode == LENNOX_HUMIDITY_MODE_HUMIDIFY:
                await self._zone.perform_humidify_setpoint(r_husp=humidity)
        except S30Exception as ex:
            err = f"set_humidity [{self._myname}] [{ex.as_string()}]"
            raise HomeAssistantError(err) from ex
        except Exception as ex:
            err = f"set_humidity unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            raise HomeAssistantError(err) from ex

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac operation modes."""
        modes = []
        if self.is_zone_disabled:
            return modes
        modes.append(HVACMode.OFF)
        if self._zone.coolingOption:
            modes.append(HVACMode.COOL)
        if self._zone.heatingOption:
            modes.append(HVACMode.HEAT)
        if self._zone.coolingOption and self._zone.heatingOption:
            modes.append(HVACMode.HEAT_COOL)
        return modes

    async def async_trigger_fast_poll(self) -> None:
        """Triggers a fast poll."""
        self._manager.mp_wakeup_event.set()

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new hvac operation mode."""
        if self.is_zone_disabled:
            err = f"Unable to set hvac_mode as zone [{self._myname}] is disabled"
            raise HomeAssistantError(err)
        try:
            t_hvac_mode = hvac_mode
            # Only this mode needs to be mapped
            if t_hvac_mode == HVACMode.HEAT_COOL:
                t_hvac_mode = LENNOX_HVAC_HEAT_COOL
            _LOGGER.info(
                "climate:async_set_hvac_mode zone [%s] ha_mode [%s] lennox_mode [%s]",
                self._myname,
                hvac_mode,
                t_hvac_mode,
            )
            await self._zone.setHVACMode(t_hvac_mode)
            await self.async_trigger_fast_poll()
        except S30Exception as ex:
            err = f"set_hvac_mode [{self._myname}] [{ex.as_string()}]"
            raise HomeAssistantError(err) from ex
        except Exception as ex:
            err = f"set_hvac_mode unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            raise HomeAssistantError(err) from ex

    def async_turn_off(self) -> None:
        """Turn off the zone."""
        _LOGGER.info("climate:async_turn_off name [%s]", self._myname)
        return self.async_set_hvac_mode(HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current hvac state/action."""
        to = self._zone.tempOperation
        ho = self._zone.humOperation
        if to not in HVACAction:
            return HVACAction.IDLE
        if to != LENNOX_TEMP_OPERATION_OFF:
            return to
        if ho != LENNOX_TEMP_OPERATION_OFF:
            if ho == LENNOX_HUMID_OPERATION_DEHUMID:
                return HVACAction.DRYING
            if ho == LENNOX_HUMID_OPERATION_WAITING:
                return HVACAction.IDLE
            return ho
        if to == LENNOX_TEMP_OPERATION_OFF and self._zone.systemMode != LENNOX_HVAC_OFF:
            return HVACAction.IDLE
        return to

    @property
    def preset_mode(self) -> str:
        """Returns current preset mode."""
        if self.is_zone_disabled:
            return None

        if self._system.get_away_mode():
            return PRESET_AWAY
        if self._zone.overrideActive:
            return PRESET_SCHEDULE_OVERRIDE
        if self._zone.isZoneManualMode():
            return PRESET_NONE
        schedule_id = self._zone.scheduleId
        if schedule_id is None:
            return PRESET_NONE
        schedule = self._system.getSchedule(schedule_id)
        if schedule is None:
            return PRESET_NONE
        return schedule.name

    @property
    def preset_modes(self) -> list[str]:
        """Returns list of preset modes."""
        presets = []
        if self.is_zone_disabled:
            return presets
        for schedule in self._system.getSchedules():
            # Everything above 16 seems to be internal schedules
            if schedule.id >= LENNOX_MANUAL_MODE_SCHEDULE_START_INDEX:
                continue
            presets.append(schedule.name)
        presets.append(PRESET_AWAY)
        presets.append(PRESET_CANCEL_HOLD)
        presets.append(PRESET_CANCEL_AWAY_MODE)
        presets.append(PRESET_SCHEDULE_OVERRIDE)
        presets.append(PRESET_NONE)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("climate:preset_modes name[%s] presets[%s]", self._myname, presets)
        return presets

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        _LOGGER.info("climate:async_set_preset_mode name [%s] preset_mode [%s]", self._myname, preset_mode)
        if self.is_zone_disabled:
            err = f"Unable to set preset mode [{preset_mode}] as zone [{self._myname}] is disabled"
            raise HomeAssistantError(err)

        if preset_mode == PRESET_SCHEDULE_OVERRIDE:
            err = f"Setting preset to {PRESET_SCHEDULE_OVERRIDE} is not a valid operation."
            raise HomeAssistantError(err)
        try:
            if preset_mode == PRESET_CANCEL_AWAY_MODE:
                processed = False
                if self._system.get_manual_away_mode():
                    await self._system.set_manual_away_mode(False)
                    processed = True
                if self._system.get_smart_away_mode():
                    await self._system.cancel_smart_away()
                    processed = True
                if processed is False:
                    _LOGGER.warning("Ignoring request to cancel away mode because system is not in away mode")
                    return
                await self.async_trigger_fast_poll()
                return
            if preset_mode == PRESET_AWAY:
                await self._system.set_manual_away_mode(True)
                await self.async_trigger_fast_poll()
                return
            # Need to cancel away modes before requesting a new preset
            if self._system.get_manual_away_mode():
                await self._system.set_manual_away_mode(False)
            if self._system.get_smart_away_mode():
                await self._system.cancel_smart_away()

            if preset_mode == PRESET_CANCEL_HOLD:
                await self._zone.setScheduleHold(False)
            elif preset_mode == PRESET_NONE:
                await self._zone.setManualMode()
            else:
                await self._zone.setSchedule(preset_mode)

            await self.async_trigger_fast_poll()

        except S30Exception as ex:
            err = f"set_preset_mode [{self._myname}] [{ex.as_string()}]"
            raise HomeAssistantError(err) from ex
        except Exception as ex:
            err = f"set_preset_mode unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            raise HomeAssistantError(err) from ex

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        if self.is_zone_disabled:
            return None
        return self._zone.getFanMode()

    @property
    def fan_modes(self) -> list[str]:
        """Return the list of available fan modes."""
        if self.is_zone_disabled:
            return []
        return FAN_MODES

    async def async_set_temperature(self, **kwargs: dict[str, Any]) -> None:
        """Set new target temperature."""
        if self.is_zone_disabled:
            err = f"Unable to set_temperature as zone [{self._myname}] is disabled"
            raise HomeAssistantError(err)

        r_hvac_mode = None
        if kwargs.get(ATTR_HVAC_MODE) is not None:
            r_hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        r_temperature = None
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            r_temperature = kwargs.get(ATTR_TEMPERATURE)
        r_csp = None
        if kwargs.get(ATTR_TARGET_TEMP_HIGH) is not None:
            r_csp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        r_hsp = None
        if kwargs.get(ATTR_TARGET_TEMP_LOW) is not None:
            r_hsp = kwargs.get(ATTR_TARGET_TEMP_LOW)

        _LOGGER.info(
            "climate:async_set_temperature zone [%s] hvacMode [%s] temperature [%s] temp_high [%s] temp_low [%s]",
            self._myname,
            r_hvac_mode,
            r_temperature,
            r_csp,
            r_hsp,
        )

        # A temperature must be specified
        if r_temperature is None and r_csp is None and r_hsp is None:
            err = f"climate:async_set_temperature - no temperature given zone [{self._myname}]] hvacMode [{r_hvac_mode}] temperature [{r_temperature}] temp_high [{r_csp}] temp_low [{r_hsp}]"  # noqa: E501
            raise HomeAssistantError(err)

        # Either provide temperature or high/low but not both
        if r_temperature is not None and (r_csp is not None or r_hsp is not None):
            err = f"climate:async_set_temperature - provide either temperature or temp_high / low - zone [{self._myname}] hvacMode [{r_hvac_mode}] temperature [{r_temperature}] temp_high [{r_csp}] temp_low [{r_hsp}]"  # noqa: E501
            raise HomeAssistantError(err)

        # If no temperature, must specify both high and low
        if r_temperature is None and (r_csp is None or r_hsp is None):
            err = f"climate:async_set_temperature - must provide both temp_high / low - zone [{self._myname}] hvacMode [{r_hvac_mode}] temperature [{r_temperature}] temp_high [{r_csp}] temp_low [{r_hsp}]"  # noqa: E501
            raise HomeAssistantError(err)

        # If single setpoint mode, then must specify r_temperature and not high and low
        if self._zone.system.single_setpoint_mode and r_temperature is None:
            err = f"climate:async_set_temperature - zone in single setpoint mode must provide [{ATTR_TEMPERATURE}] - zone [{self._myname}]"
            raise HomeAssistantError(err)

        try:
            # If an HVAC mode is requested; and we are not in that mode, then the first step
            # is to switch the zone into that mode before setting the temperature
            if r_hvac_mode is not None and r_hvac_mode != self.hvac_mode:
                _LOGGER.debug("climate:async_set_temperature zone [%s] setting hvacMode [%s]", self._myname, r_hvac_mode)
                await self.async_set_hvac_mode(r_hvac_mode)

            if r_hvac_mode is None:
                r_hvac_mode = self.hvac_mode

            if r_hvac_mode is None:
                err = f"set_temperature System Mode is [{r_hvac_mode}] unable to set temperature"
                raise S30Exception(err, EC_BAD_PARAMETERS, 10)

            if r_temperature is not None:
                if self._zone.system.single_setpoint_mode:
                    _LOGGER.debug(
                        "climate:async_set_temperature set_temperature in single_setpoint_modesystem - zone [%s] temperature [%s]",
                        self._myname,
                        r_temperature,
                    )
                    if self._manager.is_metric is False:
                        await self._zone.perform_setpoint(r_sp=r_temperature)
                    else:
                        await self._zone.perform_setpoint(r_spC=r_temperature)
                elif r_hvac_mode == HVACMode.COOL:
                    _LOGGER.debug(
                        "climate:async_set_temperature set_temperature system in cool mode - zone [%s] temperature [%s]",
                        self._myname,
                        r_temperature,
                    )
                    if self._manager.is_metric is False:
                        await self._zone.perform_setpoint(r_csp=r_temperature)
                    else:
                        await self._zone.perform_setpoint(r_cspC=r_temperature)
                elif r_hvac_mode == HVACMode.HEAT:
                    _LOGGER.debug(
                        "climate:async_set_temperature set_temperature system in heat mode - zone [%s] sp [%s]",
                        self._myname,
                        r_temperature,
                    )
                    if self._manager.is_metric is False:
                        await self._zone.perform_setpoint(r_hsp=r_temperature)
                    else:
                        await self._zone.perform_setpoint(r_hspC=r_temperature)
                else:
                    err = f"set_temperature System Mode is [{r_hvac_mode}] unable to set temperature"
                    raise S30Exception(err, EC_BAD_PARAMETERS, 11)
            else:
                _LOGGER.debug("climate:async_set_temperature zone [%s] csp [%s] hsp [%s]", self._myname, r_csp, r_hsp)
                if self._manager.is_metric is False:
                    await self._zone.perform_setpoint(r_hsp=r_hsp, r_csp=r_csp)
                else:
                    await self._zone.perform_setpoint(r_hspC=r_hsp, r_cspC=r_csp)

            await self.async_trigger_fast_poll()

        except S30Exception as ex:
            err = f"set_temperature [{self._myname}] [{ex.as_string()}]"
            raise HomeAssistantError(err) from ex
        except Exception as ex:
            err = f"set_temperature unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            raise HomeAssistantError(err) from ex

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        _LOGGER.info("climate:async_set_fan_mode name [%s] fanMode [%s]", self._myname, fan_mode)
        if self.is_zone_disabled:
            err = f"Unable to set_fan_mode as zone [{self._myname}] is disabled"
            raise HomeAssistantError(err)
        try:
            await self._zone.setFanMode(fan_mode)
            await self.async_trigger_fast_poll()

        except S30Exception as ex:
            err = f"set_fan_mode [{self._myname}] [{ex.as_string()}]"
            raise HomeAssistantError(err) from ex
        except Exception as ex:
            err = f"set_fan_mode unexpected exception, please log issue, [{self._myname}] exception [{ex}]"
            raise HomeAssistantError(err) from ex

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
        }
