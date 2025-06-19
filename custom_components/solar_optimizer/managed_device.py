""" A ManagedDevice represent a device than can be managed by the optimisatiion algorithm"""
import logging
from datetime import datetime, timedelta, time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.components.select import SelectEntity
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN

from .const import (
    get_tz,
    name_to_unique_id,
    get_template_or_value,
    get_safe_float,
    convert_to_template_or_value,
    CONF_ACTION_MODE_ACTION,
    CONF_ACTION_MODE_EVENT,
    CONF_ACTION_MODES,
    ConfigurationError,
    EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
    EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
    EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
)

ACTION_ACTIVATE = "Activate"
ACTION_DEACTIVATE = "Deactivate"
ACTION_CHANGE_POWER = "ChangePower"

# Entity domains that require attribute to change power
POWERED_ENTITY_DOMAINS_NEED_ATTR = (
    LIGHT_DOMAIN,
    FAN_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def do_service_action(
    hass: HomeAssistant,
    entity_id,
    action_type,
    service_name,
    current_power,
    requested_power,
    convert_power_divide_factor,
):
    """Activate an entity via a service call"""

    if service_name is None or len(service_name) == 0:
        _LOGGER.info(
            "No service name defined for entity %s. Cannot call service",
            entity_id,
        )
        return

    _LOGGER.info("Calling service %s for entity %s", service_name, entity_id)
    parties = service_name.split("/")
    if len(parties) < 2:
        raise ConfigurationError(
            f"Incorrect service declaration for entity {entity_id}. Service {service_name} should be formatted with: 'domain/action[/option:value]'"
        )

    service_data = {}
    domain = parties[0]
    action = parties[1]
    parameter = parties[2] if len(parties) == 3 else None

    attributes = "value" # default data key for most entities

    if action_type == ACTION_CHANGE_POWER:
        value = round(requested_power / convert_power_divide_factor)
        if parameter:
            attributes = parameter
        service_data = {attributes: value}
    else:
        if parameter:
            args = parameter.split(":")
            if len(args) >= 2:
                service_data = {args[0]: args[1]}

    target = {
        "entity_id": entity_id,
    }

    try:
        await hass.services.async_call(
            domain, action, service_data=service_data, target=target
        )
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception(err)

    # Also send an event to inform
    do_event_action(
        hass,
        entity_id,
        action_type,
        current_power,
        requested_power,
        EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER if action_type == ACTION_CHANGE_POWER else EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
    )


def do_event_action(
    hass: HomeAssistant,
    entity_id,
    action_type,
    current_power,
    requested_power,
    event_type: str,
):
    """Activate an entity via an event"""
    _LOGGER.info(
        "Sending event %s with action %s for entity %s with requested_power %s and current_power %s",
        event_type,
        action_type,
        entity_id,
        requested_power,
        current_power,
    )

    hass.bus.fire(
        event_type=event_type,
        event_data={
            "action_type": action_type,
            "requested_power": requested_power,
            "current_power": current_power,
            "entity_id": entity_id,
        },
    )


class ManagedDevice:
    """A Managed device representation"""

    def __init__(self, hass: HomeAssistant, device_config, coordinator):
        """Initialize a manageable device"""
        self._now = None  # For testing purpose only
        self._current_tz = get_tz(hass)

        self._hass = hass
        self._coordinator = coordinator
        self._name = device_config.get("name")
        self._unique_id = name_to_unique_id(self._name)
        self._entity_id = device_config.get("entity_id")
        self._power_entity_id = device_config.get("power_entity_id")
        self._power_max = convert_to_template_or_value(hass, device_config.get("power_max"))

        self._power_min = (
            int(device_config.get("power_min"))
            if device_config.get("power_min") is not None
            else -1
        )
        self._power_step = (
            int(device_config.get("power_step"))
            if device_config.get("power_step") is not None
            else 0
        )
        self._can_change_power = self._power_min >= 0
        self._convert_power_divide_factor = int(
            device_config.get("convert_power_divide_factor") or 1
        )

        self._current_power = self._requested_power = 0
        duration_min = float(device_config.get("duration_min"))
        self._duration_sec = round(duration_min * 60)
        self._duration_power_sec = round(
            float(device_config.get("duration_power_min") or duration_min) * 60
        )

        self._duration_stop_sec = round(
            float(device_config.get("duration_stop_min") or duration_min) * 60
        )

        if device_config.get("check_usable_template"):
            self._check_usable_template = Template(
                device_config.get("check_usable_template"), hass
            )
        else:
            # If no template for usability, the device is supposed to be always usable
            self._check_usable_template = Template("{{ True }}", hass)
        if device_config.get("check_active_template"):
            self._check_active_template = Template(
                device_config.get("check_active_template"), hass
            )
        else:
            template_string = (
                "{{ is_state('" + self._entity_id + "', '" + STATE_ON + "') }}"
            )
            self._check_active_template = Template(template_string, hass)
        self._next_date_available_power = self._next_date_available = self.now
        self._action_mode = device_config.get("action_mode")
        self._activation_service = device_config.get("activation_service")
        self._deactivation_service = device_config.get("deactivation_service")
        self._change_power_service = device_config.get("change_power_service")

        self._battery_soc = None
        self._battery_soc_threshold = convert_to_template_or_value(hass, device_config.get("battery_soc_threshold") or 0)

        self._max_on_time_per_day_min = convert_to_template_or_value(hass, device_config.get("max_on_time_per_day_min") or 60 * 24)
        self._on_time_sec = 0

        self._min_on_time_per_day_min = convert_to_template_or_value(hass, device_config.get("min_on_time_per_day_min") or 0)

        offpeak_time = device_config.get("offpeak_time", None)
        self._offpeak_time = None

        if offpeak_time:
            self._offpeak_time = datetime.strptime(
                device_config.get("offpeak_time"), "%H:%M"
            ).time()

        if self.is_active:
            self._requested_power = self._current_power = self.power_max if self._can_change_power else self._power_min

        self._enable = True

        # Some checks
        # min_on_time_per_day_sec requires an offpeak_time
        if self.min_on_time_per_day_sec > 0 and self._offpeak_time is None:
            msg = f"configuration of device ${self.name} is incorrect. min_on_time_per_day_sec requires offpeak_time value"
            _LOGGER.error("%s - %s", self, msg)
            raise ConfigurationError(msg)

        if self.min_on_time_per_day_sec > self.max_on_time_per_day_sec:
            msg = f"configuration of device ${self.name} is incorrect. min_on_time_per_day_sec should < max_on_time_per_day_sec"
            _LOGGER.error("%s - %s", self, msg)
            raise ConfigurationError(msg)

        self._priority_entity = None

    async def _apply_action(self, action_type: str, requested_power=None):
        """Apply an action to a managed device.
        This method is a generical method for activate, deactivate, change_requested_power
        """
        _LOGGER.debug(
            "Applying action %s for entity %s. requested_power=%s",
            action_type,
            self._entity_id,
            requested_power,
        )

        if requested_power is None:
            requested_power = self._requested_power

        if self._action_mode == CONF_ACTION_MODE_ACTION:
            method = None
            entity_id = self._entity_id
            if action_type == ACTION_ACTIVATE:
                method = self._activation_service
                self.reset_next_date_available(action_type)
                if self._can_change_power:
                    self.reset_next_date_available_power()
            elif action_type == ACTION_DEACTIVATE:
                method = self._deactivation_service
                self.reset_next_date_available(action_type)
            elif action_type == ACTION_CHANGE_POWER:
                assert (
                    self._can_change_power
                ), f"Equipment {self._name} cannot change its power. We should not be there."
                method = self._change_power_service
                entity_id = self._power_entity_id
                self.reset_next_date_available_power()

            await do_service_action(
                self._hass,
                entity_id,
                action_type,
                method,
                self._current_power,
                requested_power,
                self._convert_power_divide_factor,
            )
        elif self._action_mode == CONF_ACTION_MODE_EVENT:
            do_event_action(
                self._hass,
                self._entity_id,
                action_type,
                self._current_power,
                self._requested_power,
                EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
            )
        else:
            raise ConfigurationError(
                f"Incorrect action_mode declaration for entity '{self._entity_id}'. Action_mode '{self._action_mode}' is not supported. Use one of {CONF_ACTION_MODES}"
            )

        self._current_power = self._requested_power

    async def activate(self, requested_power=None):
        """Use this method to activate this ManagedDevice"""
        return await self._apply_action(ACTION_ACTIVATE, requested_power)

    async def deactivate(self):
        """Use this method to deactivate this ManagedDevice"""
        return await self._apply_action(ACTION_DEACTIVATE, 0)

    async def change_requested_power(self, requested_power, current_power=None):
        """Use this method to change the requested power of this ManagedDevice"""
        return await self._apply_action(ACTION_CHANGE_POWER, requested_power)

    def reset_next_date_available(self, action_type):
        """Incremente the next availability date to now + _duration_sec"""
        if action_type == ACTION_ACTIVATE:
            self._next_date_available = self.now + timedelta(seconds=self._duration_sec)
        else:
            self._next_date_available = self.now + timedelta(
                seconds=self._duration_stop_sec
            )

        _LOGGER.debug(
            "Next availability date for %s is %s", self._name, self._next_date_available
        )

    def reset_next_date_available_power(self):
        """Incremente the next availability date for power change to now + _duration_power_sec"""
        self._next_date_available_power = self.now + timedelta(
            seconds=self._duration_power_sec
        )
        _LOGGER.debug(
            "Next availability date for power change for %s is %s",
            self._name,
            self._next_date_available_power,
        )

    def set_current_power_with_device_state(self):
        """Set the current power according to the real device state"""
        if not self.is_active:
            self._current_power = 0
            _LOGGER.debug(
                "Set current_power to 0 for device %s cause not active", self._name
            )
            return

        if not self._can_change_power:
            self._current_power = self.power_max
            _LOGGER.debug(
                "Set current_power to %s for device %s cause active and not can_change_power",
                self._current_power,
                self._name,
            )
            return

        power_entity_state = self._hass.states.get(self._power_entity_id)
        if not power_entity_state or power_entity_state.state in [None, STATE_UNKNOWN, STATE_UNAVAILABLE]:
            self._current_power = self._power_min
            _LOGGER.debug(
                "Set current_power to %s for device %s cause can_change_power but state is %s",
                self._current_power,
                self._name,
                power_entity_state,
            )
            return

        if self._power_entity_id.startswith(POWERED_ENTITY_DOMAINS_NEED_ATTR):
            # TODO : move this part to device initialisation, make new instance variable
            service_name = self._change_power_service # retrieve attribute from power service
            parties = self._change_power_service.split("/")
            if len(parties) < 2:
                raise ConfigurationError(
                    f"Incorrect service declaration for power entity. Service {service_name} should be formatted with: 'domain/action/attribute'"
                )
            parameter = parties[2]
            power_entity_value = power_entity_state.attributes[parameter]
        else:
            power_entity_value = power_entity_state.state

        self._current_power = round(
            float(power_entity_value) * self._convert_power_divide_factor
        )
        _LOGGER.debug(
            "Set current_power to %s for device %s cause can_change_power and amps is %s",
            self._current_power,
            self._name,
            power_entity_value,
        )

    def set_enable(self, enable: bool):
        """Enable or disable the ManagedDevice for Solar Optimizer"""
        _LOGGER.info("%s - Set enable=%s", self.name, enable)
        self._enable = enable
        self.publish_enable_state_change()

    def set_on_time(self, on_time_sec: int):
        """Set the time the underlying device was on per day"""
        _LOGGER.info("%s - Set on_time=%s", self.name, on_time_sec)
        self._on_time_sec = on_time_sec

    def set_requested_power(self, requested_power: int):
        """Set the requested power of the ManagedDevice"""
        self._requested_power = requested_power

    @property
    def is_enabled(self) -> bool:
        """return true if the managed device is enabled for solar optimisation"""
        return self._enable

    @property
    def is_active(self) -> bool:
        """Check if device is active by getting the underlying state of the device"""
        result = self._check_active_template.async_render(context={})
        if result:
            _LOGGER.debug("%s is active", self._name)

        return result

    def check_usable(self, check_battery=True) -> bool:
        """Check if the device is usable. The battery is checked optionally"""
        if self._on_time_sec >= self.max_on_time_per_day_sec:
            _LOGGER.debug(
                "%s is not usable due to max_on_time_per_day_min exceeded %d >= %d",
                self._name,
                self._on_time_sec,
                self.max_on_time_per_day_sec,
            )
            result = False
        else:
            context = {}
            now = self.now
            result = self._check_usable_template.async_render(context)
            if self._can_change_power:
                result = result and now >= self._next_date_available_power
            else:
                result = result and now >= self._next_date_available

            if not result:
                _LOGGER.debug("%s is not usable", self._name)

            if result and check_battery and self._battery_soc is not None and self.battery_soc_threshold is not None:
                if self._battery_soc < self.battery_soc_threshold:
                    result = False
                    _LOGGER.debug(
                        "%s is not usable due to battery soc threshold (%s < %s)",
                        self._name,
                        self._battery_soc,
                        self.battery_soc_threshold,
                    )

        return result

    @property
    def is_usable(self) -> bool:
        """A device is usable for optimisation if the check_usable_template returns true and
        if the device is not waiting for the end of its cycle and if the battery_soc_threshold is >= battery_soc
        and the _max_on_time_per_day_sec is not exceeded"""
        return self.check_usable(True)

    @property
    def should_be_forced_offpeak(self) -> bool:
        """True is we are offpeak and the max_on_time is not exceeded"""
        if not self.check_usable(False) or self._offpeak_time is None:
            return False

        if self._offpeak_time >= self._coordinator.raz_time:
            return (
                (self.now.time() >= self._offpeak_time or self.now.time() < self._coordinator.raz_time)
                and self._on_time_sec < self.max_on_time_per_day_sec
                and self._on_time_sec < self.min_on_time_per_day_sec
            )
        else:
            return (
                self.now.time() >= self._offpeak_time
                and self.now.time() < self._coordinator.raz_time
                and self._on_time_sec < self.max_on_time_per_day_sec
                and self._on_time_sec < self.min_on_time_per_day_sec
            )

    @property
    def is_waiting(self):
        """A device is waiting if the device is waiting for the end of its cycle"""
        result = self.now < self._next_date_available

        if result:
            _LOGGER.debug("%s is waiting", self._name)

        return result

    @property
    def name(self):
        """The name of the ManagedDevice"""
        return self._name

    @property
    def unique_id(self):
        """The id of the ManagedDevice"""
        return self._unique_id

    @property
    def power_max(self):
        """The power max of the managed device"""
        return get_template_or_value(self._hass, self._power_max)

    @property
    def power_min(self):
        """The power min of the managed device"""
        return self._power_min

    @property
    def power_step(self):
        """The power step of the managed device"""
        return self._power_step

    @property
    def duration_sec(self) -> int:
        """The duration a device is not available after a change of the managed device"""
        return self._duration_sec

    @property
    def duration_stop_sec(self) -> int:
        """The duration a device is not available after a change of the managed device to stop"""
        return self._duration_stop_sec

    @property
    def duration_power_sec(self) -> int:
        """The duration a device is not available after a change of the managed device for power change"""
        return self._duration_power_sec

    @property
    def entity_id(self) -> str:
        """The entity_id of the device"""
        return self._entity_id

    @property
    def power_entity_id(self) -> str:
        """The entity_id of the device which gives the current power"""
        return self._power_entity_id

    @property
    def current_power(self) -> int:
        """The current_power of the device"""
        return self._current_power

    @property
    def requested_power(self) -> int:
        """The requested_power of the device"""
        return self._requested_power

    @property
    def can_change_power(self) -> bool:
        """true is the device can change its power"""
        return self._can_change_power

    @property
    def next_date_available(self) -> datetime:
        """returns the next available date for state change"""
        return self._next_date_available

    @property
    def next_date_available_power(self) -> datetime:
        """return the next available date for power change"""
        return self._next_date_available_power

    @property
    def convert_power_divide_factor(self) -> int:
        """return"""
        return self._convert_power_divide_factor

    @property
    def max_on_time_per_day_sec(self) -> int:
        """The max_on_time_per_day_sec configured"""
        return get_template_or_value(self._hass, self._max_on_time_per_day_min) * 60

    @property
    def min_on_time_per_day_sec(self) -> int:
        """The min_on_time_per_day_sec configured"""
        return get_template_or_value(self._hass, self._min_on_time_per_day_min) * 60

    @property
    def offpeak_time(self) -> int:
        """The offpeak_time configured"""
        return self._offpeak_time

    @property
    def battery_soc(self) -> int:
        """The battery soc"""
        return self._battery_soc

    @property
    def battery_soc_threshold(self) -> int:
        """The battery soc"""
        return get_template_or_value(self._hass, self._battery_soc_threshold)

    def set_battery_soc(self, battery_soc):
        """Define the battery soc. This is used with is_usable
        to determine if the device is usable"""
        self._battery_soc = battery_soc

    def publish_enable_state_change(self) -> None:
        """Publish an event when the state is changed"""

        self._hass.bus.fire(
            event_type=EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
            event_data={
                "device_unique_id": self._unique_id,
                "is_enabled": self.is_enabled,
                "is_active": self.is_active,
                "is_usable": self.is_usable,
                "is_waiting": self.is_waiting,
            },
        )

    def set_priority_entity(self, entity: SelectEntity):
        """Set the priority entity"""
        self._priority_entity = entity

    @property
    def priority(self) -> int:
        """Get the priority"""
        if self._priority_entity is None:
            return 0
        return self._priority_entity.current_priority

    # For testing purpose only
    def _set_now(self, now: datetime):
        """Set the now timestamp. This is only for tests purpose"""
        self._now = now

    @property
    def now(self) -> datetime:
        """Get now. The local datetime or the overloaded _set_now date"""
        return self._now if self._now is not None else datetime.now(self._current_tz)
