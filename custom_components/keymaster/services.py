"""Services for keymaster."""
import logging
import os
import random
from typing import Any, Dict, Mapping

from homeassistant.components.input_text import MODE_PASSWORD, MODE_TEXT
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.components.persistent_notification import create
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify

from .const import (
    ATTR_CODE_SLOT,
    ATTR_NODE_ID,
    ATTR_USER_CODE,
    CONF_HIDE_PINS,
    CONF_LOCK_ENTITY_ID,
    CONF_PATH,
    CONF_SLOTS,
    CONF_START,
    DEFAULT_HIDE_PINS,
    DOMAIN,
    MANAGER,
    PRIMARY_LOCK,
)
from .exceptions import ZWaveIntegrationNotConfiguredError
from .helpers import (
    async_using_ozw,
    async_using_zwave,
    async_using_zwave_js,
    get_code_slots_list,
    get_node_id,
    output_to_file_from_template,
    reload_package_platforms,
    reset_code_slot_if_pin_unknown,
)
from .lock import KeymasterLock

# TODO: At some point we should deprecate ozw and zwave and require zwave_js.
# At that point, we will not need this try except logic and can remove a bunch
# of code.
try:
    from zwave_js_server.util.lock import get_usercode_from_node

    from homeassistant.components.zwave_js.const import DOMAIN as ZWAVE_JS_DOMAIN
    from homeassistant.components.zwave_js.helpers import async_get_node_from_entity_id
    from homeassistant.components.zwave_js.lock import (
        SERVICE_CLEAR_LOCK_USERCODE,
        SERVICE_SET_LOCK_USERCODE,
    )
except (ModuleNotFoundError, ImportError):
    pass

try:
    from openzwavemqtt.const import CommandClass

    from homeassistant.components.ozw import DOMAIN as OZW_DOMAIN
except (ModuleNotFoundError, ImportError):
    pass

_LOGGER = logging.getLogger(__name__)

SET_USERCODE = "set_usercode"
CLEAR_USERCODE = "clear_usercode"


async def init_child_locks(
    hass: HomeAssistant, start: int, slots: int, lockname: str
) -> None:
    """Populates child locks values with parent values"""
    # LOCKNAME_copy_from_parent_TEMPLATENUM
    _LOGGER.debug("Syncing lock: %s", lockname)
    for x in range(start, start + slots):
        the_service = f"{lockname}_copy_from_parent_{x}"
        _LOGGER.debug("Attempting to call script: %s", the_service)
        await call_service(hass, SCRIPT_DOMAIN, the_service)
    _LOGGER.debug("Sync complete")


async def call_service(
    hass: HomeAssistant, domain: str, service: str, service_data: Dict[str, Any] = None
):
    """Call a hass service and log a failure on an error."""
    try:
        await hass.services.async_call(
            domain, service, service_data=service_data, blocking=True
        )
    except Exception as err:
        _LOGGER.error("Error calling %s.%s service call: %s", domain, service, str(err))
        raise err


async def refresh_codes(
    hass: HomeAssistant, entity_id: str, instance_id: int = 1
) -> None:
    """Refresh lock codes."""
    try:
        config_entry = next(
            config_entry
            for config_entry in hass.config_entries.async_entries(DOMAIN)
            if config_entry.data[CONF_LOCK_ENTITY_ID] == entity_id
        )
    except StopIteration:
        _LOGGER.error("Entity ID %s not set up in keymaster", entity_id)
        return

    ent_reg = async_get_entity_registry(hass)
    if async_using_zwave_js(entity_id=entity_id, ent_reg=ent_reg):
        code_slots = get_code_slots_list(config_entry.data)
        node = async_get_node_from_entity_id(hass, entity_id, ent_reg=ent_reg)
        for code_slot in code_slots:
            await get_usercode_from_node(node, code_slot)
        return

    # OZW Button press (experimental)
    if async_using_ozw(entity_id=entity_id, ent_reg=ent_reg):
        node_id = get_node_id(hass, entity_id)
        if node_id is None:
            _LOGGER.error(
                "Problem retrieving node_id from entity %s",
                entity_id,
            )
            return

        manager = hass.data[OZW_DOMAIN][MANAGER]
        lock_values = manager.get_instance(instance_id).get_node(node_id).values()
        for value in lock_values:
            if value.command_class == CommandClass.USER_CODE and value.index == 255:
                _LOGGER.debug(
                    "DEBUG: Index found valueIDKey: %s", int(value.value_id_key)
                )
                value.send_value(True)
                value.send_value(False)


async def add_code(
    hass: HomeAssistant, entity_id: str, code_slot: int, usercode: str
) -> None:
    """Set a user code."""
    _LOGGER.debug("Attempting to call set_usercode...")

    servicedata = {
        ATTR_CODE_SLOT: code_slot,
        ATTR_USER_CODE: usercode,
    }

    if async_using_zwave_js(
        entity_id=entity_id, ent_reg=async_get_entity_registry(hass)
    ):
        servicedata[ATTR_ENTITY_ID] = entity_id
        await call_service(
            hass, ZWAVE_JS_DOMAIN, SERVICE_SET_LOCK_USERCODE, servicedata
        )

    elif async_using_ozw(entity_id=entity_id, ent_reg=async_get_entity_registry(hass)):
        servicedata[ATTR_ENTITY_ID] = entity_id
        await call_service(hass, OZW_DOMAIN, SET_USERCODE, servicedata)

    elif async_using_zwave(
        entity_id=entity_id, ent_reg=async_get_entity_registry(hass)
    ):
        node_id = get_node_id(hass, entity_id)
        if node_id is None:
            _LOGGER.error(
                "Problem retrieving node_id from entity %s",
                entity_id,
            )
            return

        servicedata[ATTR_NODE_ID] = node_id
        await call_service(hass, LOCK_DOMAIN, SET_USERCODE, servicedata)

    else:
        raise ZWaveIntegrationNotConfiguredError


async def clear_code(hass: HomeAssistant, entity_id: str, code_slot: int) -> None:
    """Clear the usercode from a code slot."""
    _LOGGER.debug("Attempting to call clear_usercode...")

    if async_using_zwave_js(
        entity_id=entity_id, ent_reg=async_get_entity_registry(hass)
    ):
        servicedata = {
            ATTR_ENTITY_ID: entity_id,
            ATTR_CODE_SLOT: code_slot,
        }
        await call_service(
            hass, ZWAVE_JS_DOMAIN, SERVICE_CLEAR_LOCK_USERCODE, servicedata
        )

    elif async_using_ozw(entity_id=entity_id, ent_reg=async_get_entity_registry(hass)):
        # Call dummy slot first as a workaround
        for curr_code_slot in (999, code_slot):
            servicedata = {
                ATTR_ENTITY_ID: entity_id,
                ATTR_CODE_SLOT: curr_code_slot,
            }
            await call_service(hass, OZW_DOMAIN, CLEAR_USERCODE, servicedata)

    elif async_using_zwave(
        entity_id=entity_id, ent_reg=async_get_entity_registry(hass)
    ):
        node_id = get_node_id(hass, entity_id)
        if node_id is None:
            _LOGGER.error(
                "Problem retrieving node_id from entity %s",
                entity_id,
            )
            return

        servicedata = {
            ATTR_NODE_ID: node_id,
            ATTR_CODE_SLOT: code_slot,
        }

        _LOGGER.debug(
            "Setting code slot value to random PIN as workaround in case clearing code "
            "doesn't work"
        )
        await call_service(
            hass,
            LOCK_DOMAIN,
            SET_USERCODE,
            {**servicedata, ATTR_USER_CODE: str(random.randint(1000, 9999))},
        )

        await call_service(hass, LOCK_DOMAIN, CLEAR_USERCODE, servicedata)
    else:
        raise ZWaveIntegrationNotConfiguredError


def generate_package_files(hass: HomeAssistant, name: str) -> None:
    """Generate the package files."""
    config_entry = next(
        (
            hass.config_entries.async_get_entry(entry_id)
            for entry_id in hass.data[DOMAIN]
            if isinstance(hass.data[DOMAIN][entry_id], Mapping)
            and hass.data[DOMAIN][entry_id][PRIMARY_LOCK].lock_name == name
        ),
        None,
    )
    if not config_entry:
        raise ValueError(f"Couldn't find existing lock entry for {name}")

    primary_lock: KeymasterLock = hass.data[DOMAIN][config_entry.entry_id][PRIMARY_LOCK]

    # Append _child to child lock yaml files
    child_file = ""
    if primary_lock.parent is not None:
        child_file = "_child"

    lockname = slugify(primary_lock.lock_name)

    _LOGGER.debug("Starting file generation...")

    create(
        hass,
        (
            f"Package file generation for `{lockname}` has started. Once complete, we "
            "will attempt to automatically update Home Assistant to avoid requiring "
            "a full restart."
        ),
        title=f"{DOMAIN.title()} - Starting package file generation",
    )

    _LOGGER.debug("DEBUG conf_lock: %s name: %s", lockname, name)

    if lockname != name:
        return

    inputlockpinheader = f"input_text.{lockname}_pin"
    activelockheader = f"binary_sensor.active_{lockname}"
    input_reset_code_slot_header = f"input_boolean.reset_codeslot_{lockname}"
    lockentityname = primary_lock.lock_entity_id
    sensorname = lockname
    doorsensorentityname = primary_lock.door_sensor_entity_id or ""
    sensoralarmlevel = primary_lock.alarm_level_or_user_code_entity_id or "sensor.fake"
    sensoralarmtype = (
        primary_lock.alarm_type_or_access_control_entity_id or "sensor.fake"
    )
    hide_pins = (
        MODE_PASSWORD
        if config_entry.data.get(CONF_HIDE_PINS, DEFAULT_HIDE_PINS)
        else MODE_TEXT
    )

    output_path = os.path.join(
        hass.config.path(), config_entry.data[CONF_PATH], lockname
    )
    input_path = os.path.dirname(__file__)

    # If packages folder exists, delete it so we can recreate it
    if os.path.isdir(output_path):
        _LOGGER.debug("Directory %s already exists, cleaning it up", output_path)
        for file in os.listdir(output_path):
            os.remove(os.path.join(output_path, file))
    else:
        _LOGGER.debug("Creating packages directory %s", output_path)
        try:
            os.makedirs(output_path)
        except Exception as err:
            _LOGGER.critical("Error creating directory: %s", str(err))

    _LOGGER.debug("Packages directory is ready for file generation")

    # Generate list of code slots
    code_slots = config_entry.data[CONF_SLOTS]
    start_from = config_entry.data[CONF_START]

    activelockheaders = ",".join(
        [f"{activelockheader}_{x}" for x in range(start_from, start_from + code_slots)]
    )
    inputlockpinheaders = ",".join(
        [
            f"{inputlockpinheader}_{x}"
            for x in range(start_from, start_from + code_slots)
        ]
    )
    input_reset_code_slot_headers = ",".join(
        [
            f"{input_reset_code_slot_header}_{x}"
            for x in range(start_from, start_from + code_slots)
        ]
    )

    _LOGGER.debug("Creating common YAML files...")
    replacements = {
        "LOCKNAME": lockname,
        "CASE_LOCK_NAME": lockname,
        "INPUTLOCKPINHEADER": inputlockpinheaders,
        "ACTIVELOCKHEADER": activelockheaders,
        "INPUT_RESET_CODE_SLOT_HEADER": input_reset_code_slot_headers,
        "LOCKENTITYNAME": lockentityname,
        "SENSORNAME": sensorname,
        "DOORSENSORENTITYNAME": doorsensorentityname,
        "SENSORALARMTYPE": sensoralarmtype,
        "SENSORALARMLEVEL": sensoralarmlevel,
        "HIDE_PINS": hide_pins,
        "PARENTLOCK": "" if primary_lock.parent is None else primary_lock.parent,
    }

    # Replace variables in common file
    for in_f, out_f, write_mode in (
        (
            f"keymaster_common{child_file}.yaml",
            f"{lockname}_keymaster_common.yaml",
            "w+",
        ),
        (f"lovelace{child_file}.head", f"{lockname}_lovelace", "w+"),
    ):
        output_to_file_from_template(
            input_path, in_f, output_path, out_f, replacements, write_mode
        )

    _LOGGER.debug("Creating per slot YAML and lovelace cards...")
    # Replace variables in code slot files
    for x in range(start_from, start_from + code_slots):
        replacements["TEMPLATENUM"] = str(x)

        for in_f, out_f, write_mode in (
            (f"keymaster{child_file}.yaml", f"{lockname}_keymaster_{x}.yaml", "w+"),
            (f"lovelace{child_file}.code", f"{lockname}_lovelace", "a"),
        ):
            output_to_file_from_template(
                input_path, in_f, output_path, out_f, replacements, write_mode
            )

    if reload_package_platforms(hass):
        create(
            hass,
            (
                f"Package generation for `{lockname}` complete!\n\n"
                "All changes have been automatically applied, so no restart is needed."
            ),
            title=f"{DOMAIN.title()} - Package file generation complete!",
        )
        _LOGGER.debug(
            "Package generation complete and all changes have been hot reloaded"
        )
        reset_code_slot_if_pin_unknown(hass, lockname, code_slots, start_from)
        if primary_lock.parent is not None:
            init_child_locks(hass, start_from, code_slots, lockname)
    else:
        create(
            hass,
            (
                f"Package generation for `{lockname}` complete!\n\n"
                "Changes couldn't be automatically applied, so a Home Assistant "
                "restart is needed to fully apply the changes."
            ),
            title=f"{DOMAIN.title()} - Package file generation complete!",
        )
        _LOGGER.debug("Package generation complete, Home Assistant restart needed")
