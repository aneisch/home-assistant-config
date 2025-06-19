""" Alls constants for the Solar Optimizer integration. """

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN


from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import

types_schema_devices = vol.Schema(
    {
        vol.Required(
            CONF_DEVICE_TYPE, default=CONF_DEVICE
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_DEVICE_TYPES,
                translation_key="device_type",
                mode="list",
            )
        )
    }
)

central_config_schema = vol.Schema(
    {
        vol.Required(CONF_REFRESH_PERIOD_SEC, default=300): int,
        vol.Required(CONF_POWER_CONSUMPTION_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Required(CONF_POWER_PRODUCTION_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Optional(CONF_SUBSCRIBE_TO_EVENTS, default=False): cv.boolean,
        vol.Required(CONF_SELL_COST_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Required(CONF_BUY_COST_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Required(CONF_SELL_TAX_PERCENT_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Optional(CONF_SMOOTH_PRODUCTION, default=True): cv.boolean,
        vol.Optional(CONF_BATTERY_SOC_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Optional(CONF_BATTERY_CHARGE_POWER_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
        ),
        vol.Optional(CONF_RAZ_TIME, default=DEFAULT_RAZ_TIME): str,
    }
)

managed_device_schema = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[INPUT_BOOLEAN_DOMAIN, SWITCH_DOMAIN, HUMIDIFIER_DOMAIN, CLIMATE_DOMAIN, FAN_DOMAIN, LIGHT_DOMAIN, SELECT_DOMAIN, BUTTON_DOMAIN])
        ),
        vol.Required(CONF_POWER_MAX): str,
        vol.Optional(CONF_CHECK_USABLE_TEMPLATE, default="{{ True }}"): str,
        vol.Optional(CONF_CHECK_ACTIVE_TEMPLATE): str,
        vol.Optional(CONF_DURATION_MIN, default="60"): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1440, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_DURATION_STOP_MIN): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1440, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_ACTION_MODE, default=CONF_ACTION_MODE_ACTION): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_ACTION_MODES,
                translation_key="action_mode",
                mode="dropdown",
            )
        ),
        vol.Required(CONF_ACTIVATION_SERVICE, default="switch/turn_on"): str,
        vol.Optional(CONF_DEACTIVATION_SERVICE, default="switch/turn_off"): str,
        vol.Optional(CONF_BATTERY_SOC_THRESHOLD, default=0): str,
        vol.Optional(CONF_MAX_ON_TIME_PER_DAY_MIN): str,
        vol.Optional(CONF_MIN_ON_TIME_PER_DAY_MIN): str,
        vol.Optional(CONF_OFFPEAK_TIME): str,
    }
)

power_managed_device_schema = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[
                    INPUT_BOOLEAN_DOMAIN,
                    SWITCH_DOMAIN,
                    HUMIDIFIER_DOMAIN,
                    CLIMATE_DOMAIN,
                    FAN_DOMAIN,
                    LIGHT_DOMAIN,
                ]
            )
        ),
        vol.Optional(CONF_POWER_ENTITY_ID): selector.EntitySelector(selector.EntitySelectorConfig(
            domain=[
                INPUT_NUMBER_DOMAIN,
                NUMBER_DOMAIN,
                FAN_DOMAIN,
                LIGHT_DOMAIN,
            ]
        )),
        vol.Optional(CONF_POWER_MIN, default=220): vol.Coerce(float),
        vol.Required(CONF_POWER_MAX): str,
        vol.Optional(CONF_POWER_STEP, default=220): vol.Coerce(float),
        vol.Optional(CONF_CHECK_USABLE_TEMPLATE, default="{{ True }}"): str,
        vol.Optional(CONF_CHECK_ACTIVE_TEMPLATE): str,
        vol.Optional(CONF_DURATION_MIN, default="60"): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1440, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_DURATION_STOP_MIN): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1440, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_DURATION_POWER_MIN): selector.NumberSelector(selector.NumberSelectorConfig(min=0.0, max=1440, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_ACTION_MODE, default=CONF_ACTION_MODE_ACTION): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=CONF_ACTION_MODES,
                translation_key="action_mode",
                mode="dropdown",
            )
        ),
        vol.Required(CONF_ACTIVATION_SERVICE, default="switch/turn_on"): str,
        vol.Required(CONF_DEACTIVATION_SERVICE, default="switch/turn_off"): str,
        vol.Optional(CONF_CHANGE_POWER_SERVICE, default="number/set_value"): str,
        vol.Optional(CONF_CONVERT_POWER_DIVIDE_FACTOR, default=220): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1.0, max=9999, step=0.1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_BATTERY_SOC_THRESHOLD, default=0): str,
        vol.Optional(CONF_MAX_ON_TIME_PER_DAY_MIN): str,
        vol.Optional(CONF_MIN_ON_TIME_PER_DAY_MIN): str,
        vol.Optional(CONF_OFFPEAK_TIME): str,
    }
)
