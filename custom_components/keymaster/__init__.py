"""keymaster Integration."""
import asyncio
from datetime import timedelta
import functools
import logging
from typing import Any, Dict, List, Optional, Union

import voluptuous as vol

from homeassistant.components.persistent_notification import async_create, async_dismiss
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_LOCKED,
    STATE_ON,
    STATE_UNLOCKED,
)
from homeassistant.core import Config, CoreState, Event, HomeAssistant, ServiceCall
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    async_get as async_get_entity_registry,
)
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from .binary_sensor import generate_binary_sensor_name
from .const import (
    ATTR_CODE_SLOT,
    ATTR_NAME,
    ATTR_NODE_ID,
    ATTR_USER_CODE,
    CHILD_LOCKS,
    CONF_ALARM_LEVEL,
    CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID,
    CONF_ALARM_TYPE,
    CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID,
    CONF_CHILD_LOCKS_FILE,
    CONF_ENTITY_ID,
    CONF_GENERATE,
    CONF_HIDE_PINS,
    CONF_LOCK_ENTITY_ID,
    CONF_LOCK_NAME,
    CONF_PARENT,
    CONF_PATH,
    CONF_SLOTS,
    CONF_START,
    COORDINATOR,
    DEFAULT_HIDE_PINS,
    DOMAIN,
    INTEGRATION,
    ISSUE_URL,
    MANAGER,
    PLATFORMS,
    PRIMARY_LOCK,
    UNSUB_LISTENERS,
    VERSION,
    ZWAVE_NETWORK,
)
from .exceptions import (
    NoNodeSpecifiedError,
    NotFoundError as NativeNotFoundError,
    NotSupportedError as NativeNotSupportedError,
    ZWaveIntegrationNotConfiguredError,
    ZWaveNetworkNotReady,
)
from .helpers import (
    async_reload_package_platforms,
    async_reset_code_slot_if_pin_unknown,
    async_using_ozw,
    async_using_zwave,
    async_using_zwave_js,
    delete_folder,
    delete_lock_and_base_folder,
    generate_keymaster_locks,
    get_code_slots_list,
    get_node_id,
    handle_state_change,
    handle_zwave_js_event,
)
from .lock import KeymasterLock
from .services import (
    add_code,
    clear_code,
    generate_package_files,
    init_child_locks,
    refresh_codes,
)

# TODO: At some point we should deprecate ozw and zwave and require zwave_js.
# At that point, we will not need this try except logic and can remove a bunch
# of code.
try:
    from zwave_js_server.const.command_class.lock import ATTR_IN_USE, ATTR_USERCODE
    from zwave_js_server.model.node import Node as ZwaveJSNode
    from zwave_js_server.util.lock import get_usercode_from_node, get_usercodes

    from homeassistant.components.zwave_js import ZWAVE_JS_NOTIFICATION_EVENT
except (ModuleNotFoundError, ImportError):
    pass

try:
    from homeassistant.components.ozw import DOMAIN as OZW_DOMAIN
except (ModuleNotFoundError, ImportError):
    pass

try:
    from openzwavemqtt.const import CommandClass
    from openzwavemqtt.exceptions import NotFoundError
    from openzwavemqtt.util.node import get_node_from_manager
except (ModuleNotFoundError, ImportError):
    pass

_LOGGER = logging.getLogger(__name__)

SERVICE_GENERATE_PACKAGE = "generate_package"
SERVICE_ADD_CODE = "add_code"
SERVICE_CLEAR_CODE = "clear_code"
SERVICE_REFRESH_CODES = "refresh_codes"

SET_USERCODE = "set_usercode"
CLEAR_USERCODE = "clear_usercode"


async def homeassistant_started_listener(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    locks_to_watch: List[KeymasterLock],
    evt: Event = None,
):
    """Start tracking state changes after HomeAssistant has started."""
    # Listen to lock state changes so we can fire an event
    hass.data[DOMAIN][config_entry.entry_id][UNSUB_LISTENERS].append(
        async_track_state_change(
            hass,
            [lock.lock_entity_id for lock in locks_to_watch],
            functools.partial(handle_state_change, hass, config_entry),
            from_state=[STATE_LOCKED, STATE_UNLOCKED],
            to_state=[STATE_LOCKED, STATE_UNLOCKED],
        )
    )


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Disallow configuration via YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up is called when Home Assistant is loading our component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(
        "Version %s is starting, if you have any issues please report" " them here: %s",
        VERSION,
        ISSUE_URL,
    )
    should_generate_package = config_entry.data.get(CONF_GENERATE)

    updated_config = config_entry.data.copy()

    # pop CONF_GENERATE if it is in data
    updated_config.pop(CONF_GENERATE, None)

    # If CONF_PATH is absolute, make it relative. This can be removed in the future,
    # it is only needed for entries that are being migrated from using the old absolute
    # path
    config_path = hass.config.path()
    if config_entry.data[CONF_PATH].startswith(config_path):
        num_chars_config_path = len(config_path)
        updated_config[CONF_PATH] = updated_config[CONF_PATH][num_chars_config_path:]
        # Remove leading slashes
        updated_config[CONF_PATH] = updated_config[CONF_PATH].lstrip("/").lstrip("\\")

    if "parent" not in config_entry.data.keys():
        updated_config[CONF_PARENT] = None
    elif config_entry.data[CONF_PARENT] == "(none)":
        updated_config[CONF_PARENT] = None

    if updated_config != config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data=updated_config)

    config_entry.add_update_listener(update_listener)

    primary_lock, child_locks = await generate_keymaster_locks(hass, config_entry)

    hass.data[DOMAIN][config_entry.entry_id] = {
        PRIMARY_LOCK: primary_lock,
        CHILD_LOCKS: child_locks,
        UNSUB_LISTENERS: [],
    }
    coordinator = LockUsercodeUpdateCoordinator(
        hass, config_entry, async_get_entity_registry(hass)
    )
    hass.data[DOMAIN][config_entry.entry_id][COORDINATOR] = coordinator

    # Button Press
    async def _refresh_codes(service: ServiceCall) -> None:
        """Refresh lock codes."""
        _LOGGER.debug("Refresh Codes service: %s", service)
        entity_id = service.data[ATTR_ENTITY_ID]
        instance_id = 1
        await refresh_codes(hass, entity_id, instance_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_CODES,
        _refresh_codes,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Coerce(str),
            }
        ),
    )

    # Add code
    async def _add_code(service: ServiceCall) -> None:
        """Set a user code."""
        _LOGGER.debug("Add Code service: %s", service)
        entity_id = service.data[ATTR_ENTITY_ID]
        code_slot = service.data[ATTR_CODE_SLOT]
        usercode = service.data[ATTR_USER_CODE]
        await add_code(hass, entity_id, code_slot, usercode)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_CODE,
        _add_code,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Coerce(str),
                vol.Required(ATTR_CODE_SLOT): vol.Coerce(int),
                vol.Required(ATTR_USER_CODE): vol.Coerce(str),
            }
        ),
    )

    # Clear code
    async def _clear_code(service: ServiceCall) -> None:
        """Clear a user code."""
        _LOGGER.debug("Clear Code service: %s", service)
        entity_id = service.data[ATTR_ENTITY_ID]
        code_slot = service.data[ATTR_CODE_SLOT]
        await clear_code(hass, entity_id, code_slot)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_CODE,
        _clear_code,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.Coerce(str),
                vol.Required(ATTR_CODE_SLOT): vol.Coerce(int),
            }
        ),
    )

    # Generate package files
    def _generate_package(service: ServiceCall) -> None:
        """Generate the package files."""
        _LOGGER.debug("DEBUG: %s", service)
        name = service.data[ATTR_NAME]
        generate_package_files(hass, name)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_PACKAGE,
        _generate_package,
        schema=vol.Schema({vol.Optional(ATTR_NAME): vol.Coerce(str)}),
    )

    await async_reset_code_slot_if_pin_unknown(
        hass,
        primary_lock.lock_name,
        config_entry.data[CONF_SLOTS],
        config_entry.data[CONF_START],
    )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    # if the use turned on the bool generate the files
    if should_generate_package:
        servicedata = {"lockname": primary_lock.lock_name}
        await hass.services.async_call(
            DOMAIN, SERVICE_GENERATE_PACKAGE, servicedata, blocking=True
        )

    if async_using_zwave_js(lock=primary_lock):
        # Listen to Z-Wave JS events so we can fire our own events
        hass.data[DOMAIN][config_entry.entry_id][UNSUB_LISTENERS].append(
            hass.bus.async_listen(
                ZWAVE_JS_NOTIFICATION_EVENT,
                functools.partial(handle_zwave_js_event, hass, config_entry),
            )
        )
        await system_health_check(hass, config_entry)
        return True

    # We only get here if we are not using zwave_js

    # Check if we need to check alarm type/alarm level sensors, in which case
    # we need to listen for lock state changes
    locks_to_watch = []
    for lock in [primary_lock, *child_locks]:
        if (
            lock.alarm_level_or_user_code_entity_id
            not in (
                None,
                "sensor.fake",
            )
            and lock.alarm_type_or_access_control_entity_id not in (None, "sensor.fake")
        ):
            locks_to_watch.append(lock)

    if locks_to_watch:
        if hass.state == CoreState.running:
            await homeassistant_started_listener(hass, config_entry, locks_to_watch)
        else:
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                functools.partial(
                    homeassistant_started_listener, hass, config_entry, locks_to_watch
                ),
            )

    if primary_lock.parent is not None:
        await init_child_locks(
            hass,
            config_entry.data[CONF_START],
            config_entry.data[CONF_SLOTS],
            config_entry.data[CONF_LOCK_NAME],
        )

    await system_health_check(hass, config_entry)
    return True


async def system_health_check(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update system health check data."""
    primary_lock = hass.data[DOMAIN][config_entry.entry_id][PRIMARY_LOCK]

    if async_using_zwave_js(lock=primary_lock):
        hass.data[DOMAIN][INTEGRATION] = "zwave_js"
    elif async_using_ozw(lock=primary_lock):
        hass.data[DOMAIN][INTEGRATION] = "ozw"
    elif async_using_zwave(lock=primary_lock):
        hass.data[DOMAIN][INTEGRATION] = "zwave"
    else:
        hass.data[DOMAIN][INTEGRATION] = "unknown"

    hass.data[DOMAIN]["network_sensor"] = slugify(f"{primary_lock.lock_name}: Network")


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    lockname = config_entry.data[CONF_LOCK_NAME]
    notification_id = f"{DOMAIN}_{lockname}_unload"
    async_create(
        hass,
        (
            f"Removing `{lockname}` and all of the files that were generated for "
            "it. This may take some time so don't panic. This message will "
            "automatically clear when removal is complete."
        ),
        title=f"{DOMAIN.title()} - Removing `{lockname}`",
        notification_id=notification_id,
    )

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        # Remove all package files and the base folder if needed
        await hass.async_add_executor_job(
            delete_lock_and_base_folder, hass, config_entry
        )

        await async_reload_package_platforms(hass)

        # Unsubscribe to any listeners
        for unsub_listener in hass.data[DOMAIN][config_entry.entry_id].get(
            UNSUB_LISTENERS, []
        ):
            unsub_listener()
        hass.data[DOMAIN][config_entry.entry_id].get(UNSUB_LISTENERS, []).clear()

        hass.data[DOMAIN].pop(config_entry.entry_id)

    async_dismiss(hass, notification_id)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    version = config_entry.version

    # 1 -> 2: Migrate to new keys
    if version == 1:
        _LOGGER.debug("Migrating from version %s", version)
        data = config_entry.data.copy()

        data[CONF_ALARM_LEVEL_OR_USER_CODE_ENTITY_ID] = data.pop(CONF_ALARM_LEVEL, None)
        data[CONF_ALARM_TYPE_OR_ACCESS_CONTROL_ENTITY_ID] = data.pop(
            CONF_ALARM_TYPE, None
        )
        data[CONF_LOCK_ENTITY_ID] = data.pop(CONF_ENTITY_ID)
        if CONF_HIDE_PINS not in data:
            data[CONF_HIDE_PINS] = DEFAULT_HIDE_PINS
        data[CONF_CHILD_LOCKS_FILE] = data.get(CONF_CHILD_LOCKS_FILE, "")

        hass.config_entries.async_update_entry(entry=config_entry, data=data)
        config_entry.version = 2
        _LOGGER.debug("Migration to version %s complete", config_entry.version)

    return True


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener."""
    # No need to update if the options match the data
    if not config_entry.options:
        return

    # If the path has changed delete the old base folder, otherwise if the lock name
    # has changed only delete the old lock folder
    if config_entry.options[CONF_PATH] != config_entry.data[CONF_PATH]:
        await hass.async_add_executor_job(
            delete_folder, hass.config.path(), config_entry.data[CONF_PATH]
        )
    elif config_entry.options[CONF_LOCK_NAME] != config_entry.data[CONF_LOCK_NAME]:
        await hass.async_add_executor_job(
            delete_folder,
            hass.config.path(),
            config_entry.data[CONF_PATH],
            config_entry.data[CONF_LOCK_NAME],
        )

    old_slots = get_code_slots_list(config_entry.data)
    new_slots = get_code_slots_list(config_entry.options)

    new_data = config_entry.options.copy()
    new_data.pop(CONF_GENERATE, None)

    hass.config_entries.async_update_entry(
        entry=config_entry,
        unique_id=config_entry.options[CONF_LOCK_NAME],
        data=new_data,
        options={},
    )

    primary_lock, child_locks = await generate_keymaster_locks(hass, config_entry)

    hass.data[DOMAIN][config_entry.entry_id].update(
        {
            PRIMARY_LOCK: primary_lock,
            CHILD_LOCKS: child_locks,
        }
    )
    servicedata = {"lockname": primary_lock.lock_name}
    await hass.services.async_call(
        DOMAIN, SERVICE_GENERATE_PACKAGE, servicedata, blocking=True
    )

    if old_slots != new_slots:
        async_dispatcher_send(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_code_slots_changed",
            old_slots,
            new_slots,
        )

    # Unsubscribe to any listeners so we can create new ones
    for unsub_listener in hass.data[DOMAIN][config_entry.entry_id].get(
        UNSUB_LISTENERS, []
    ):
        unsub_listener()
    hass.data[DOMAIN][config_entry.entry_id].get(UNSUB_LISTENERS, []).clear()

    if async_using_zwave_js(lock=primary_lock):
        hass.data[DOMAIN][config_entry.entry_id][UNSUB_LISTENERS].append(
            hass.bus.async_listen(
                ZWAVE_JS_NOTIFICATION_EVENT,
                functools.partial(handle_zwave_js_event, hass, config_entry),
            )
        )
        return

    # We only get here if we are not using zwave_js

    # Check if alarm type/alarm level sensors are specified, in which case
    # we need to listen for lock state changes and derive the action from those
    # sensors
    locks_to_watch = []
    for lock in [primary_lock, *child_locks]:
        if (
            lock.alarm_level_or_user_code_entity_id
            not in (
                None,
                "sensor.fake",
            )
            and lock.alarm_type_or_access_control_entity_id not in (None, "sensor.fake")
        ):
            locks_to_watch.append(lock)

    if locks_to_watch:
        # Create new listeners for lock state changes
        hass.data[DOMAIN][config_entry.entry_id][UNSUB_LISTENERS].append(
            async_track_state_change(
                hass,
                [lock.lock_entity_id for lock in locks_to_watch],
                functools.partial(handle_state_change, hass, config_entry),
                from_state=[STATE_LOCKED, STATE_UNLOCKED],
                to_state=[STATE_LOCKED, STATE_UNLOCKED],
            )
        )


class LockUsercodeUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage usercode updates."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, ent_reg: EntityRegistry
    ) -> None:
        self._primary_lock: KeymasterLock = hass.data[DOMAIN][config_entry.entry_id][
            PRIMARY_LOCK
        ]
        self._child_locks: List[KeymasterLock] = hass.data[DOMAIN][
            config_entry.entry_id
        ][CHILD_LOCKS]
        self.config_entry = config_entry
        self.ent_reg = ent_reg
        self.network_sensor = None
        self.slots = None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
            update_method=self.async_update_usercodes,
        )
        self.data = {}

    def _invalid_code(self, code_slot):
        """Return the PIN slot value as we are unable to read the slot value
        from the lock."""

        _LOGGER.debug("Work around code in use.")
        # This is a fail safe and should not be needing to return ""
        data = ""

        # Build data from entities
        active_binary_sensor = (
            f"binary_sensor.active_{self._primary_lock.lock_name}_{code_slot}"
        )
        active = self.hass.states.get(active_binary_sensor)
        pin_data = f"input_text.{self._primary_lock.lock_name}_pin_{code_slot}"
        pin = self.hass.states.get(pin_data)

        # If slot is enabled return the PIN
        if active is not None and pin is not None:
            if active.state == "on" and pin.state.isnumeric():
                _LOGGER.debug("Utilizing BE469 work around code.")
                data = pin.state
            else:
                _LOGGER.debug("Utilizing FE599 work around code.")
                data = ""

        return data

    async def async_update_usercodes(self) -> Dict[Union[str, int], Any]:
        """Wrapper to update usercodes."""
        self.slots = get_code_slots_list(self.config_entry.data)
        if not self.network_sensor:
            self.network_sensor = self.ent_reg.async_get_entity_id(
                "binary_sensor",
                DOMAIN,
                slugify(generate_binary_sensor_name(self._primary_lock.lock_name)),
            )
        if self.network_sensor is None:
            raise UpdateFailed
        try:
            network_ready = self.hass.states.get(self.network_sensor)
            if not network_ready:
                # We may need to get a new entity ID
                self.network_sensor = None
                raise ZWaveNetworkNotReady

            if network_ready.state != STATE_ON:
                raise ZWaveNetworkNotReady

            return await self._async_update()
        except (
            NativeNotFoundError,
            NativeNotSupportedError,
            NoNodeSpecifiedError,
            ZWaveIntegrationNotConfiguredError,
            ZWaveNetworkNotReady,
        ) as err:
            # We can silently fail if we've never been able to retrieve data
            if not self.data:
                return {}
            raise UpdateFailed from err

    async def _async_update(self) -> Dict[Union[str, int], Any]:
        """Update usercodes."""
        # loop to get user code data from entity_id node
        instance_id = 1  # default
        data = {CONF_LOCK_ENTITY_ID: self._primary_lock.lock_entity_id}

        # # make button call
        # servicedata = {"entity_id": self._entity_id}
        # await self.hass.services.async_call(
        #    DOMAIN, SERVICE_REFRESH_CODES, servicedata
        # )

        if async_using_zwave_js(lock=self._primary_lock):
            node: ZwaveJSNode = self._primary_lock.zwave_js_lock_node
            if node is None:
                raise NativeNotFoundError
            code_slot = 1

            for slot in get_usercodes(node):
                code_slot = int(slot[ATTR_CODE_SLOT])
                usercode: Optional[str] = slot[ATTR_USERCODE]
                in_use: Optional[bool] = slot[ATTR_IN_USE]
                # Retrieve code slots that haven't been populated yet
                if in_use is None and code_slot in self.slots:
                    usercode_resp = await get_usercode_from_node(node, code_slot)
                    usercode = slot[ATTR_USERCODE] = usercode_resp[ATTR_USERCODE]
                    in_use = slot[ATTR_IN_USE] = usercode_resp[ATTR_IN_USE]
                if not in_use:
                    _LOGGER.debug("DEBUG: Code slot %s not enabled", code_slot)
                    data[code_slot] = ""
                elif usercode and "*" in str(usercode):
                    _LOGGER.debug(
                        "DEBUG: Ignoring code slot with * in value for code slot %s",
                        code_slot,
                    )
                    data[code_slot] = self._invalid_code(code_slot)
                else:
                    _LOGGER.debug("DEBUG: Code slot %s value: %s", code_slot, usercode)
                    data[code_slot] = usercode

        # pull the codes for ozw
        elif async_using_ozw(lock=self._primary_lock):
            node_id = get_node_id(self.hass, self._primary_lock.lock_entity_id)
            if node_id is None:
                return data
            data[ATTR_NODE_ID] = node_id

            if data[ATTR_NODE_ID] is None:
                raise NoNodeSpecifiedError
            # Raises exception when node not found
            try:
                node = get_node_from_manager(
                    self.hass.data[OZW_DOMAIN][MANAGER],
                    instance_id,
                    data[ATTR_NODE_ID],
                )
            except NotFoundError:
                raise NativeNotFoundError from None

            command_class = node.get_command_class(CommandClass.USER_CODE)

            if not command_class:
                raise NativeNotSupportedError("Node doesn't have code slots")

            for value in command_class.values():  # type: ignore
                code_slot = int(value.index)
                _LOGGER.debug(
                    "DEBUG: Code slot %s value: %s", code_slot, str(value.value)
                )
                if value.value and "*" in str(value.value):
                    _LOGGER.debug("DEBUG: Ignoring code slot with * in value.")
                    data[code_slot] = self._invalid_code(code_slot)
                else:
                    data[code_slot] = value.value

        # pull codes for zwave
        elif async_using_zwave(lock=self._primary_lock):
            node_id = get_node_id(self.hass, self._primary_lock.lock_entity_id)
            if node_id is None:
                return data
            data[ATTR_NODE_ID] = node_id

            if data[ATTR_NODE_ID] is None:
                raise NoNodeSpecifiedError

            network = self.hass.data[ZWAVE_NETWORK]
            node = network.nodes.get(data[ATTR_NODE_ID])
            if not node:
                raise NativeNotFoundError

            lock_values = node.get_values(class_id=CommandClass.USER_CODE).values()
            for value in lock_values:
                _LOGGER.debug(
                    "DEBUG: Code slot %s value: %s",
                    str(value.index),
                    str(value.data),
                )
                # do not update if the code contains *s
                code = str(value.data)

                # Remove \x00 if found
                code = code.replace("\x00", "")

                # Check for * in lock data and use workaround code if exist
                if "*" in code:
                    _LOGGER.debug("DEBUG: Ignoring code slot with * in value.")
                    code = self._invalid_code(value.index)

                # Build data from entities
                active_binary_sensor = (
                    f"binary_sensor.active_{self._primary_lock.lock_name}_{value.index}"
                )
                active = self.hass.states.get(active_binary_sensor)

                # Report blank slot if occupied by random code
                if active is not None:
                    if active.state == "off":
                        _LOGGER.debug(
                            "DEBUG: Utilizing Zwave clear_usercode work around code"
                        )
                        code = ""

                data[int(value.index)] = code

        else:
            raise ZWaveIntegrationNotConfiguredError

        return data
