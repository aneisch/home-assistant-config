""" Les constantes pour l'intégration Solar Optimizer """

import re
import logging
import math
from slugify import slugify
from voluptuous.error import Invalid

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.helpers.template import Template, is_template_string

SOLAR_OPTIMIZER_DOMAIN = DOMAIN = "solar_optimizer"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]

DEVICE_MANUFACTURER = "JMCOLLIN"
DEVICE_MODEL = "Solar Optimizer"

DEFAULT_REFRESH_PERIOD_SEC = 300
DEFAULT_RAZ_TIME = "05:00"

CONF_ACTION_MODE_ACTION = "action_call"
CONF_ACTION_MODE_EVENT = "event"

CONF_ACTION_MODES = [CONF_ACTION_MODE_ACTION, CONF_ACTION_MODE_EVENT]

EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER = "solar_optimizer_change_power_event"
EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE = "solar_optimizer_state_change_event"

EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE = (
    "solar_optimizer_enable_state_change_event"
)

DEVICE_MODEL = "Solar Optimizer device"
INTEGRATION_MODEL = "Solar Optimizer"
DEVICE_MANUFACTURER = "JM. COLLIN"

SERVICE_RESET_ON_TIME = "reset_on_time"

TIME_REGEX = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
CONFIG_VERSION = 2
CONFIG_MINOR_VERSION = 1

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_CENTRAL = "central_config"
CONF_DEVICE = "device_type"
CONF_POWERED_DEVICE = "powered_device_type"
CONF_ALL_CONFIG_TYPES = [CONF_DEVICE_CENTRAL, CONF_DEVICE, CONF_POWERED_DEVICE]
CONF_DEVICE_TYPES = [CONF_DEVICE, CONF_POWERED_DEVICE]
CONF_POWER_CONSUMPTION_ENTITY_ID = "power_consumption_entity_id"
CONF_POWER_PRODUCTION_ENTITY_ID = "power_production_entity_id"
CONF_SUBSCRIBE_TO_EVENTS = "subscribe_to_events"
CONF_SELL_COST_ENTITY_ID = "sell_cost_entity_id"
CONF_BUY_COST_ENTITY_ID = "buy_cost_entity_id"
CONF_SELL_TAX_PERCENT_ENTITY_ID = "sell_tax_percent_entity_id"
CONF_SMOOTH_PRODUCTION = "smooth_production"
CONF_REFRESH_PERIOD_SEC = "refresh_period_sec"
CONF_NAME = "name"
CONF_ENTITY_ID = "entity_id"
CONF_POWER_MAX = "power_max"
CONF_CHECK_USABLE_TEMPLATE = "check_usable_template"
CONF_CHECK_ACTIVE_TEMPLATE = "check_active_template"
CONF_DURATION_MIN = "duration_min"
CONF_DURATION_STOP_MIN = "duration_stop_min"
CONF_ACTION_MODE = "action_mode"
CONF_ACTIVATION_SERVICE = "activation_service"
CONF_DEACTIVATION_SERVICE = "deactivation_service"
CONF_POWER_MIN = "power_min"
CONF_POWER_STEP = "power_step"
CONF_POWER_ENTITY_ID = "power_entity_id"
CONF_DURATION_POWER_MIN = "duration_power_min"
CONF_CHANGE_POWER_SERVICE = "change_power_service"
CONF_CONVERT_POWER_DIVIDE_FACTOR = "convert_power_divide_factor"
CONF_RAZ_TIME = "raz_time"
CONF_BATTERY_SOC_ENTITY_ID = "battery_soc_entity_id"
CONF_BATTERY_CHARGE_POWER_ENTITY_ID = "battery_charge_power_entity_id"
CONF_BATTERY_SOC_THRESHOLD = "battery_soc_threshold"
CONF_MAX_ON_TIME_PER_DAY_MIN = "max_on_time_per_day_min"
CONF_MIN_ON_TIME_PER_DAY_MIN = "min_on_time_per_day_min"
CONF_OFFPEAK_TIME = "offpeak_time"

PRIORITY_WEIGHT_NULL = "None"
PRIORITY_WEIGHT_LOW = "Low"
PRIORITY_WEIGHT_MEDIUM = "Medium"
PRIORITY_WEIGHT_HIGH = "High"
PRIORITY_WEIGHT_VERY_HIGH = "Very high"
PRIORITY_WEIGHTS = [
    PRIORITY_WEIGHT_NULL,
    PRIORITY_WEIGHT_LOW,
    PRIORITY_WEIGHT_MEDIUM,
    PRIORITY_WEIGHT_HIGH,
    PRIORITY_WEIGHT_VERY_HIGH,
]

# Gives the percentage of priority in the cost calculation. 10 means 10%
PRIORITY_WEIGHT_MAP = {
    PRIORITY_WEIGHT_NULL: 0,
    PRIORITY_WEIGHT_LOW: 10,
    PRIORITY_WEIGHT_MEDIUM: 25,
    PRIORITY_WEIGHT_HIGH: 50,
    PRIORITY_WEIGHT_VERY_HIGH: 75,
}


PRIORITY_VERY_LOW = "Very low"
PRIORITY_LOW = "Low"
PRIORITY_MEDIUM = "Medium"
PRIORITY_HIGH = "High"
PRIORITY_VERY_HIGH = "Very high"
PRIORITIES = [
    PRIORITY_VERY_LOW,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_HIGH,
    PRIORITY_VERY_HIGH,
]

PRIORITY_MAP = {
    PRIORITY_VERY_LOW: 16,
    PRIORITY_LOW: 8,
    PRIORITY_MEDIUM: 4,
    PRIORITY_HIGH: 2,
    PRIORITY_VERY_HIGH: 1,
}


_LOGGER = logging.getLogger(__name__)

def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


def name_to_unique_id(name: str) -> str:
    """Convert a name to a unique id. Replace ' ' by _"""
    return slugify(name).replace("-", "_")


def seconds_to_hms(seconds):
    """Convert seconds to a formatted string of hours:minutes:seconds."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def validate_time_format(value: str) -> str:
    """check is a string have format "hh:mm" with hh between 00 and 23 and mm between 00 et 59"""
    if value is not None and not re.match(TIME_REGEX, value):
        raise Invalid("The time value should be formatted like 'hh:mm'")
    return value


def get_safe_float(hass, str_as_float) -> float | None:
    """Get a safe float state value for an str_as_float string.
    Return None if str_as_float is None or not a valid float.
    """
    if str_as_float is None:
        return None

    if isinstance(str_as_float, int):
        return float(str_as_float)

    if isinstance(str_as_float, float):
        return str_as_float

    str_as_float = str_as_float.strip()
    try:
        float_val = float(str_as_float)
        return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val
    except Exception as exc:
        _LOGGER.error("Error converting %s to float %s. SolarOptimizer will not work until this issue is fixed.", str_as_float, exc)
        raise exc


def get_template_or_value(hass: HomeAssistant, value):
    """Get the template or the value"""
    if isinstance(value, Template):
        return value.async_render(context={})
    return value


def convert_to_template_or_value(hass: HomeAssistant, value):
    """Convert the value to a template or a value"""
    if isinstance(value, str):
        if is_template_string(value):
            return Template(value, hass)
    if isinstance(value, str):
        value = value.strip()
    if value == "None":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    return get_safe_float(hass, value)


class ConfigurationError(Exception):
    """An error in configuration"""

    def __init__(self, message):
        super().__init__(message)


class overrides:  # pylint: disable=invalid-name
    """An annotation to inform overrides"""

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"Method {self.func.__name__} should have been overridden")

class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""


class InvalidTime(HomeAssistantError):
    """Error to indicate the give time is invalid"""
