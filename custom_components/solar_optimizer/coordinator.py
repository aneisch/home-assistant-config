""" The data coordinator class """

import logging
import math
from datetime import datetime, timedelta, time
from typing import Any

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.components.select import SelectEntity

from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    PowerConverter
)

from homeassistant.config_entries import ConfigEntry

from .const import DEFAULT_REFRESH_PERIOD_SEC, name_to_unique_id, SOLAR_OPTIMIZER_DOMAIN, DEFAULT_RAZ_TIME
from .managed_device import ManagedDevice
from .simulated_annealing_algo import SimulatedAnnealingAlgorithm

_LOGGER = logging.getLogger(__name__)


def get_safe_float(hass, entity_id: str, unit: str = None):
    """Get a safe float state value for an entity.
    Return None if entity is not available"""
    if entity_id is None or not (state := hass.states.get(entity_id)) or state.state == "unknown" or state.state == "unavailable":
        return None

    float_val = float(state.state)

    if (unit is not None) and ('device_class' in state.attributes) and (state.attributes["device_class"] == "power"):
        float_val = PowerConverter.convert(float_val,
            state.attributes["unit_of_measurement"],
            unit
        )

    return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val


class SolarOptimizerCoordinator(DataUpdateCoordinator):
    """The coordinator class which is used to coordinate all update"""

    hass: HomeAssistant

    def __init__(self, hass: HomeAssistant, config):
        """Initialize the coordinator"""
        SolarOptimizerCoordinator.hass = hass
        self._devices: list[ManagedDevice] = []
        self._power_consumption_entity_id: str = None
        self._power_production_entity_id: str = None
        self._subscribe_to_events: bool = False
        self._unsub_events = None
        self._sell_cost_entity_id: str = None
        self._buy_cost_entity_id: str = None
        self._sell_tax_percent_entity_id: str = None
        self._smooth_production: bool = True
        self._last_production: float = 0.0
        self._battery_soc_entity_id: str = None
        self._battery_charge_power_entity_id: str = None
        self._raz_time: time = None

        self._central_config_done = False
        self._priority_weight_entity = None

        super().__init__(hass, _LOGGER, name="Solar Optimizer")

        init_temp = 1000
        min_temp = 0.05
        cooling_factor = 0.95
        max_iteration_number = 1000

        if config and (algo_config := config.get("algorithm")):
            init_temp = float(algo_config.get("initial_temp", 1000))
            min_temp = float(algo_config.get("min_temp", 0.05))
            cooling_factor = float(algo_config.get("cooling_factor", 0.95))
            max_iteration_number = int(algo_config.get("max_iteration_number", 1000))

        self._algo = SimulatedAnnealingAlgorithm(
            init_temp, min_temp, cooling_factor, max_iteration_number
        )
        self.config = config

    async def configure(self, config: ConfigEntry) -> None:
        """Configure the coordinator from configEntry of the integration"""
        refresh_period_sec = (
            config.data.get("refresh_period_sec") or DEFAULT_REFRESH_PERIOD_SEC
        )
        self.update_interval = timedelta(seconds=refresh_period_sec)
        self._schedule_refresh()

        self._power_consumption_entity_id = config.data.get(
            "power_consumption_entity_id"
        )
        self._power_production_entity_id = config.data.get("power_production_entity_id")
        self._subscribe_to_events = config.data.get("subscribe_to_events")

        if self._unsub_events is not None:
            self._unsub_events()
            self._unsub_events = None

        if self._subscribe_to_events:
            self._unsub_events = async_track_state_change_event(
                self.hass,
                [self._power_consumption_entity_id, self._power_production_entity_id],
                self._async_on_change)

        self._sell_cost_entity_id = config.data.get("sell_cost_entity_id")
        self._buy_cost_entity_id = config.data.get("buy_cost_entity_id")
        self._sell_tax_percent_entity_id = config.data.get("sell_tax_percent_entity_id")
        self._battery_soc_entity_id = config.data.get("battery_soc_entity_id")
        self._battery_charge_power_entity_id = config.data.get(
            "battery_charge_power_entity_id"
        )
        self._smooth_production = config.data.get("smooth_production") is True
        self._last_production = 0.0

        self._raz_time = datetime.strptime(
            config.data.get("raz_time") or DEFAULT_RAZ_TIME, "%H:%M"
        ).time()
        self._central_config_done = True

    async def on_ha_started(self, _) -> None:
        """Listen the homeassistant_started event to initialize the first calculation"""
        _LOGGER.info("First initialization of Solar Optimizer")

    async def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        await self.async_refresh()
        self._schedule_refresh()

    async def _async_update_data(self):
        _LOGGER.info("Refreshing Solar Optimizer calculation")

        calculated_data = {}

        # Add a device state attributes
        for _, device in enumerate(self._devices):
            # Initialize current power depending or reality
            device.set_current_power_with_device_state()

        # Add a power_consumption and power_production
        power_production = get_safe_float(self.hass, self._power_production_entity_id, "W")
        if power_production is None:
            _LOGGER.warning(
                "Power production is not valued. Solar Optimizer will be disabled"
            )
            return None

        if not self._smooth_production:
            calculated_data["power_production"] = power_production
        else:
            self._last_production = round(
                0.5 * self._last_production + 0.5 * power_production
            )
            calculated_data["power_production"] = self._last_production

        calculated_data["power_production_brut"] = power_production

        calculated_data["power_consumption"] = get_safe_float(
            self.hass, self._power_consumption_entity_id, "W"
        )

        calculated_data["sell_cost"] = get_safe_float(
            self.hass, self._sell_cost_entity_id
        )

        calculated_data["buy_cost"] = get_safe_float(
            self.hass, self._buy_cost_entity_id
        )

        calculated_data["sell_tax_percent"] = get_safe_float(
            self.hass, self._sell_tax_percent_entity_id
        )

        soc = get_safe_float(self.hass, self._battery_soc_entity_id)
        calculated_data["battery_soc"] = soc if soc is not None else 0

        charge_power = get_safe_float(self.hass, self._battery_charge_power_entity_id)
        calculated_data["battery_charge_power"] = (
            charge_power if charge_power is not None else 0
        )

        calculated_data["priority_weight"] = self.priority_weight

        #
        # Call Algorithm Recuit simulé
        #
        best_solution, best_objective, total_power = self._algo.recuit_simule(
            self._devices,
            calculated_data["power_consumption"] + calculated_data["battery_charge_power"],
            calculated_data["power_production"],
            calculated_data["sell_cost"],
            calculated_data["buy_cost"],
            calculated_data["sell_tax_percent"],
            calculated_data["battery_soc"],
            calculated_data["priority_weight"],
        )

        calculated_data["best_solution"] = best_solution
        calculated_data["best_objective"] = best_objective
        calculated_data["total_power"] = total_power

        # Uses the result to turn on or off or change power
        should_log = False
        for _, equipement in enumerate(best_solution):
            name = equipement["name"]
            requested_power = equipement.get("requested_power")
            state = equipement["state"]
            _LOGGER.debug("Dealing with best_solution for %s - %s", name, equipement)
            device = self.get_device_by_name(name)
            if not device:
                continue

            old_requested_power = device.requested_power
            is_active = device.is_active
            should_force_offpeak = device.should_be_forced_offpeak
            if should_force_offpeak:
                _LOGGER.debug("%s - we should force %s name", self, name)
            if is_active and not state and not should_force_offpeak:
                _LOGGER.debug("Extinction de %s", name)
                should_log = True
                old_requested_power = 0
                await device.deactivate()
            elif not is_active and (state or should_force_offpeak):
                _LOGGER.debug("Allumage de %s", name)
                should_log = True
                old_requested_power = requested_power
                await device.activate(requested_power)

            # Send change power if state is now on and change power is accepted and (power have change or eqt is just activated)
            if (
                state
                and device.can_change_power
                and (device.current_power != requested_power or not is_active)
            ):
                _LOGGER.debug(
                    "Change power of %s to %s",
                    equipement["name"],
                    requested_power,
                )
                should_log = True
                await device.change_requested_power(requested_power)

            device.set_requested_power(old_requested_power)

            # Add updated data to the result
            calculated_data[name_to_unique_id(name)] = device

        if should_log:
            _LOGGER.info("Calculated data are: %s", calculated_data)
        else:
            _LOGGER.debug("Calculated data are: %s", calculated_data)

        return calculated_data

    @classmethod
    def get_coordinator(cls) -> Any:
        """Get the coordinator from the hass.data"""
        if (
            not hasattr(SolarOptimizerCoordinator, "hass")
            or SolarOptimizerCoordinator.hass is None
            or SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN] is None
        ):
            return None

        return SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN][
            "coordinator"
        ]

    @classmethod
    def reset(cls) -> Any:
        """Reset the coordinator from the hass.data"""
        if (
            not hasattr(SolarOptimizerCoordinator, "hass")
            or SolarOptimizerCoordinator.hass is None
            or SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN] is None
        ):
            return

        SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN][
            "coordinator"
        ] = None

    @property
    def is_central_config_done(self) -> bool:
        """Return True if the central config is done"""
        return self._central_config_done

    @property
    def devices(self) -> list[ManagedDevice]:
        """Get all the managed device"""
        return self._devices

    def get_device_by_name(self, name: str) -> ManagedDevice | None:
        """Returns the device which name is given in argument"""
        for _, device in enumerate(self._devices):
            if device.name == name:
                return device
        return None

    def get_device_by_unique_id(self, uid: str) -> ManagedDevice | None:
        """Returns the device which name is given in argument"""
        for _, device in enumerate(self._devices):
            if device.unique_id == uid:
                return device
        return None

    def set_priority_weight_entity(self, entity: SelectEntity):
        """Set the priority weight entity"""
        self._priority_weight_entity = entity

    @property
    def priority_weight(self) -> int:
        """Get the priority weight"""
        if self._priority_weight_entity is None:
            return 0
        return self._priority_weight_entity.current_priority_weight

    @property
    def raz_time(self) -> time:
        """Get the raz time with default to DEFAULT_RAZ_TIME"""
        return self._raz_time

    def add_device(self, device: ManagedDevice):
        """Add a new device to the list of managed device"""
        # Append or replace the device
        for i, dev in enumerate(self._devices):
            if dev.unique_id == device.unique_id:
                self._devices[i] = device
                return
        self._devices.append(device)

    def remove_device(self, unique_id: str):
        """Remove a device from the list of managed device"""
        for i, dev in enumerate(self._devices):
            if dev.unique_id == unique_id:
                self._devices.pop(i)
                return
