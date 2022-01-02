"""Adds config flow for keymaster."""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

import voluptuous as vol
from voluptuous.schema_builder import ALLOW_EXTRA

from homeassistant import config_entries
from homeassistant.components.binary_sensor import DOMAIN as BINARY_DOMAIN
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSORS_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util import slugify
from homeassistant.util.yaml.loader import load_yaml

from .const import (
    CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID,
    CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID,
    CONF_GENERATE,
    CONF_HIDE_PINS,
    CONF_LOCK_ENTITY_ID,
    CONF_LOCK_NAME,
    CONF_PARENT,
    CONF_PATH,
    CONF_SENSOR_NAME,
    CONF_SLOTS,
    CONF_START,
    DEFAULT_ALARM_LEVEL_SENSOR,
    DEFAULT_ALARM_TYPE_SENSOR,
    DEFAULT_CODE_SLOTS,
    DEFAULT_DOOR_SENSOR,
    DEFAULT_GENERATE,
    DEFAULT_HIDE_PINS,
    DEFAULT_PACKAGES_PATH,
    DEFAULT_START,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CHILD_LOCKS_SCHEMA = cv.schema_with_slug_keys(
    {
        vol.Required(CONF_LOCK_ENTITY_ID): cv.entity_id,
        vol.Optional(
            CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID, default="sensor.fake"
        ): vol.Any(None, cv.entity_id),
        vol.Optional(
            CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID, default="sensor.fake"
        ): vol.Any(None, cv.entity_id),
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class KeyMasterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for KeyMaster."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    DEFAULTS = {
        CONF_SLOTS: DEFAULT_CODE_SLOTS,
        CONF_START: DEFAULT_START,
        CONF_SENSOR_NAME: DEFAULT_DOOR_SENSOR,
        CONF_PATH: DEFAULT_PACKAGES_PATH,
        CONF_HIDE_PINS: DEFAULT_HIDE_PINS,
    }

    async def _get_unique_name_error(self, user_input) -> Dict[str, str]:
        """Check if name is unique, returning dictionary error if so."""
        # Validate that lock name is unique
        existing_entry = await self.async_set_unique_id(
            user_input[CONF_LOCK_NAME], raise_on_progress=True
        )
        if existing_entry:
            return {CONF_LOCK_NAME: "same_name"}
        return {}

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        return await _start_config_flow(
            self,
            "user",
            user_input[CONF_LOCK_NAME] if user_input else None,
            user_input,
            self.DEFAULTS,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return KeyMasterOptionsFlow(config_entry)


class KeyMasterOptionsFlow(config_entries.OptionsFlow):
    """Options flow for KeyMaster."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize."""
        self.config_entry = config_entry

    def _get_unique_name_error(self, user_input):
        """Check if name is unique, returning dictionary error if so."""
        # If lock name has changed, make sure new name isn't already being used
        # otherwise show an error
        if self.config_entry.unique_id != user_input[CONF_LOCK_NAME]:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.unique_id == user_input[CONF_LOCK_NAME]:
                    return {CONF_LOCK_NAME: "same_name"}
        return {}

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        return await _start_config_flow(
            self,
            "init",
            "",
            user_input,
            self.config_entry.data,
            self.config_entry.entry_id,
        )


def _available_parent_locks(hass: HomeAssistant, entry_id: str = None) -> list:
    """Find other keymaster configurations and list them as posible
    parent locks if they are not a child lock already."""

    data = ["(none)"]
    if DOMAIN not in hass.data:
        return data

    for entry in hass.config_entries.async_entries(DOMAIN):
        if CONF_PARENT not in entry.data.keys() and entry.entry_id != entry_id:
            data.append(entry.title)
        elif entry.data[CONF_PARENT] is None and entry.entry_id != entry_id:
            data.append(entry.title)

    return data


def _get_entities(
    hass: HomeAssistant,
    domain: str,
    search: List[str] = None,
    extra_entities: List[str] = None,
) -> List[str]:
    data = []
    if domain not in hass.data:
        return data

    for entity in hass.data[domain].entities:
        if search is not None and not any(map(entity.entity_id.__contains__, search)):
            continue
        data.append(entity.entity_id)

    if extra_entities:
        data.extend(extra_entities)

    return data


def _get_schema(
    hass: HomeAssistant,
    user_input: Optional[Dict[str, Any]],
    default_dict: Dict[str, Any],
    entry_id: str = None,
) -> vol.Schema:
    """Gets a schema using the default_dict as a backup."""
    if user_input is None:
        user_input = {}

    if CONF_PARENT in default_dict.keys() and default_dict[CONF_PARENT] is None:
        check_dict = default_dict.copy()
        check_dict.pop(CONF_PARENT, None)
        default_dict = check_dict

    def _get_default(key: str, fallback_default: Any = None) -> None:
        """Gets default value for key."""
        return user_input.get(key, default_dict.get(key, fallback_default))

    return vol.Schema(
        {
            vol.Optional(
                CONF_PARENT, default=_get_default(CONF_PARENT, "(none)")
            ): vol.In(_available_parent_locks(hass, entry_id)),
            vol.Required(
                CONF_LOCK_ENTITY_ID, default=_get_default(CONF_LOCK_ENTITY_ID)
            ): vol.In(_get_entities(hass, LOCK_DOMAIN)),
            vol.Required(
                CONF_SLOTS, default=_get_default(CONF_SLOTS, DEFAULT_CODE_SLOTS)
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_START, default=_get_default(CONF_START, DEFAULT_START)
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(CONF_LOCK_NAME, default=_get_default(CONF_LOCK_NAME)): str,
            vol.Optional(
                CONF_SENSOR_NAME,
                default=_get_default(CONF_SENSOR_NAME, DEFAULT_DOOR_SENSOR),
            ): vol.In(
                _get_entities(hass, BINARY_DOMAIN, extra_entities=[DEFAULT_DOOR_SENSOR])
            ),
            vol.Optional(
                CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID,
                default=_get_default(
                    CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID, DEFAULT_ALARM_LEVEL_SENSOR
                ),
            ): vol.In(
                _get_entities(
                    hass,
                    SENSORS_DOMAIN,
                    search=["alarm_level", "user_code", "alarmlevel"],
                    extra_entities=[DEFAULT_ALARM_LEVEL_SENSOR],
                )
            ),
            vol.Optional(
                CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID,
                default=_get_default(
                    CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID,
                    DEFAULT_ALARM_TYPE_SENSOR,
                ),
            ): vol.In(
                _get_entities(
                    hass,
                    SENSORS_DOMAIN,
                    search=["alarm_type", "access_control", "alarmtype"],
                    extra_entities=[DEFAULT_ALARM_TYPE_SENSOR],
                )
            ),
            vol.Required(
                CONF_PATH, default=_get_default(CONF_PATH, DEFAULT_PACKAGES_PATH)
            ): str,
            vol.Required(
                CONF_HIDE_PINS, default=_get_default(CONF_HIDE_PINS, DEFAULT_HIDE_PINS)
            ): bool,
        },
        extra=ALLOW_EXTRA,
    )


def _show_config_form(
    cls: Union[KeyMasterFlowHandler, KeyMasterOptionsFlow],
    step_id: str,
    user_input: Dict[str, Any],
    errors: Dict[str, str],
    description_placeholders: Dict[str, str],
    defaults: Dict[str, Any] = None,
    entry_id: str = None,
) -> Dict[str, Any]:
    """Show the configuration form to edit location data."""
    return cls.async_show_form(
        step_id=step_id,
        data_schema=_get_schema(cls.hass, user_input, defaults, entry_id),
        errors=errors,
        description_placeholders=description_placeholders,
    )


async def _start_config_flow(
    cls: Union[KeyMasterFlowHandler, KeyMasterOptionsFlow],
    step_id: str,
    title: str,
    user_input: Dict[str, Any],
    defaults: Dict[str, Any] = None,
    entry_id: str = None,
):
    """Start a config flow."""
    errors = {}
    description_placeholders = {}

    if user_input is not None:
        user_input[CONF_GENERATE] = DEFAULT_GENERATE
        user_input[CONF_LOCK_NAME] = slugify(user_input[CONF_LOCK_NAME].lower())

        # Convert (none) to None
        if user_input[CONF_PARENT] == "(none)":
            user_input[CONF_PARENT] = None

        # Regular flow has an async function, options flow has a sync function
        # so we need to handle them conditionally
        if asyncio.iscoroutinefunction(cls._get_unique_name_error):
            errors.update(await cls._get_unique_name_error(user_input))
        else:
            errors.update(cls._get_unique_name_error(user_input))

        # Validate that package path is relative
        if os.path.isabs(user_input[CONF_PATH]):
            errors[CONF_PATH] = "invalid_path"

        # Update options if no errors
        if not errors:
            return cls.async_create_entry(title=title, data=user_input)

        return _show_config_form(
            cls,
            step_id,
            user_input,
            errors,
            description_placeholders,
            defaults,
            entry_id,
        )

    return _show_config_form(
        cls,
        step_id,
        user_input,
        errors,
        description_placeholders,
        defaults,
        entry_id,
    )
