"""Support for Lennoxs30 cloud api"""
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name

import asyncio
import logging
import re
import time
from asyncio.locks import Event

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_HOSTS,
    CONF_PASSWORD,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import StateInfo
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from lennoxs30api import (
    EC_HTTP_ERR,
    EC_LOGIN,
    EC_UNAUTHORIZED,
    S30Exception,
    lennox_system,
    s30api_async,
)
from lennoxs30api.s30exception import EC_COMMS_ERROR, EC_CONFIG_TIMEOUT

from .const import (
    CONF_ALLERGEN_DEFENDER_SWITCH,
    CONF_APP_ID,
    CONF_CLOUD_CONNECTION,
    CONF_CREATE_DIAGNOSTICS_SENSORS,
    CONF_CREATE_INVERTER_POWER,
    CONF_CREATE_PARAMETERS,
    CONF_CREATE_SENSORS,
    CONF_FAST_POLL_COUNT,
    CONF_FAST_POLL_INTERVAL,
    CONF_INIT_WAIT_TIME,
    CONF_LOG_MESSAGES_TO_FILE,
    CONF_MESSAGE_DEBUG_FILE,
    CONF_MESSAGE_DEBUG_LOGGING,
    CONF_PII_IN_MESSAGE_LOGS,
    DEFAULT_CLOUD_TIMEOUT,
    DEFAULT_LOCAL_TIMEOUT,
    LENNOX_DEFAULT_CLOUD_APP_ID,
    LENNOX_DEFAULT_LOCAL_APP_ID,
    LENNOX_DOMAIN,
    MANAGER,
    VENTILATION_EQUIPMENT_ID,
)
from .device import (
    Device,
    S30AuxiliaryUnit,
    S30ControllerDevice,
    S30IndoorUnit,
    S30OutdoorUnit,
    S30VentilationUnit,
    S30ZoneThermostat,
    S40BleDevice,
)
from .helpers import helper_create_zone_entity_name
from .util import dict_redact_fields

DOMAIN = LENNOX_DOMAIN
DOMAIN_STATE = "lennoxs30.state"
PLATFORMS = [
    "sensor",
    "climate",
    "switch",
    "number",
    "binary_sensor",
    "select",
    "button",
]

DS_CONNECTING = "Connecting"
DS_DISCONNECTED = "Disconnected"
DS_LOGIN_FAILED = "Login Failed"
DS_CONNECTED = "Connected"
DS_RETRY_WAIT = "Waiting to Retry"
DS_FAILED = "Failed"

DEFAULT_POLL_INTERVAL: int = 10
DEFAULT_LOCAL_POLL_INTERVAL: int = 1
DEFAULT_FAST_POLL_INTERVAL: float = 0.75
MAX_ERRORS = 2
RETRY_INTERVAL_SECONDS = 60

UNTRACKED_STATE_ATTRIBUTES = {
    "unrecorded_attributes": {
        "message_count",
        "send_count",
        "receive_count",
        "bytes_in",
        "bytes_out",
        "http_2xx_cnt",
        "last_receive_time",
        "last_message_time",
        "sysUpTime",
        "diagLevel",
        "softwareVersion",
        "hostname",
        "sibling_id",
        "sibling_ip",
    }
}


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOSTS, default="Cloud"): str,
                vol.Optional(CONF_SCAN_INTERVAL): cv.positive_int,
                vol.Optional(CONF_FAST_POLL_INTERVAL, default=DEFAULT_FAST_POLL_INTERVAL): cv.positive_float,
                vol.Optional(CONF_ALLERGEN_DEFENDER_SWITCH, default=False): cv.boolean,
                vol.Optional(CONF_APP_ID): cv.string,
                vol.Optional(CONF_INIT_WAIT_TIME, default=30): cv.positive_int,
                vol.Optional(CONF_CREATE_SENSORS, default=False): cv.boolean,
                vol.Optional(CONF_CREATE_INVERTER_POWER, default=False): cv.boolean,
                vol.Optional(CONF_PROTOCOL, default="https"): cv.string,
                vol.Optional(CONF_PII_IN_MESSAGE_LOGS, default=False): cv.boolean,
                vol.Optional(CONF_MESSAGE_DEBUG_LOGGING, default=True): cv.boolean,
                vol.Optional(CONF_MESSAGE_DEBUG_FILE, default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Import config as config entry."""
    hass.data[DOMAIN] = {}
    if config.get(DOMAIN) is None:
        return True

    _LOGGER.warning(
        "Configuration of the LennoxS30 platform in YAML is deprecated "
        "and will be removed; Your existing configuration "
        "has been imported into the UI automatically and can be safely removed "
        "from your configuration.yaml file"
    )
    conf_hosts: str = config.get(DOMAIN).get(CONF_HOSTS)
    host_list = []
    if conf_hosts == "Cloud":
        conf_hosts = None
        host_list.append(None)
    else:
        host_list = conf_hosts.split(",")

    for host_name in host_list:
        cloud_connection: bool = False
        if host_name is None:
            cloud_connection = True
        log_to_file = True
        if config.get(DOMAIN).get(CONF_MESSAGE_DEBUG_FILE) == "":
            log_to_file = False

        conf_scan_interval = config.get(DOMAIN).get(CONF_SCAN_INTERVAL)
        if conf_scan_interval is None:
            if cloud_connection:
                conf_scan_interval = DEFAULT_POLL_INTERVAL
            else:
                conf_scan_interval = DEFAULT_LOCAL_POLL_INTERVAL

        migration_data = {
            CONF_SCAN_INTERVAL: conf_scan_interval,
            CONF_FAST_POLL_INTERVAL: config.get(DOMAIN).get(CONF_FAST_POLL_INTERVAL),
            CONF_ALLERGEN_DEFENDER_SWITCH: config.get(DOMAIN).get(CONF_ALLERGEN_DEFENDER_SWITCH),
            CONF_APP_ID: config.get(DOMAIN).get(CONF_APP_ID),
            CONF_INIT_WAIT_TIME: config.get(DOMAIN).get(CONF_INIT_WAIT_TIME),
            CONF_CREATE_SENSORS: config.get(DOMAIN).get(CONF_CREATE_SENSORS),
            CONF_PROTOCOL: config.get(DOMAIN).get(CONF_PROTOCOL),
            CONF_PII_IN_MESSAGE_LOGS: config.get(DOMAIN).get(CONF_PII_IN_MESSAGE_LOGS),
            CONF_MESSAGE_DEBUG_LOGGING: config.get(DOMAIN).get(CONF_MESSAGE_DEBUG_LOGGING),
            CONF_MESSAGE_DEBUG_FILE: config.get(DOMAIN).get(CONF_MESSAGE_DEBUG_FILE),
            CONF_LOG_MESSAGES_TO_FILE: log_to_file,
            CONF_CLOUD_CONNECTION: cloud_connection,
        }

        if cloud_connection:
            migration_data[CONF_EMAIL] = config.get(DOMAIN).get(CONF_EMAIL)
            migration_data[CONF_PASSWORD] = config.get(DOMAIN).get(CONF_PASSWORD)
            if migration_data[CONF_APP_ID] is None:
                migration_data[CONF_APP_ID] = LENNOX_DEFAULT_CLOUD_APP_ID
        else:
            migration_data[CONF_HOST] = host_name
            if migration_data[CONF_APP_ID] is None:
                migration_data[CONF_APP_ID] = LENNOX_DEFAULT_LOCAL_APP_ID
            migration_data[CONF_CREATE_INVERTER_POWER] = config.get(DOMAIN).get(CONF_CREATE_INVERTER_POWER)
        # Make sure when migrating YAML, that any new configuration defaults are added.
        _upgrade_config(migration_data, 1)
        create_migration_task(hass, migration_data)
    return True


def create_migration_task(hass, migration_data):
    """Migrates configuration from YAML to a config_entry"""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=migration_data,
        )
    )


g_unique_id_update: dict = {}


def _upgrade_config(config: dict, current_version: int) -> int:
    if current_version == 1:
        config[CONF_FAST_POLL_COUNT] = 10
        config[CONF_TIMEOUT] = DEFAULT_CLOUD_TIMEOUT if config[CONF_CLOUD_CONNECTION] is True else DEFAULT_LOCAL_TIMEOUT
        current_version = 2
    if current_version == 2:
        config[CONF_CREATE_DIAGNOSTICS_SENSORS] = False
        current_version = 3
    if current_version == 3:
        if config[CONF_CLOUD_CONNECTION] is False:
            config[CONF_CREATE_PARAMETERS] = False
        current_version = 4
    # Version 4 to 5 is a unique id update, flag it here.
    if current_version == 4:
        g_unique_id_update[4] = True
        current_version = 5
    return current_version


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Upgrades configuration from old to new version"""
    _LOGGER.info("Upgrading configuration for [%s] from version [%d]", config_entry.title, config_entry.version)
    new = {**config_entry.data}
    old_version = config_entry.version
    new_version = _upgrade_config(new, old_version)
    if new_version > old_version:
        config_entry.version = new_version
        hass.config_entries.async_update_entry(config_entry, data=new)
        _LOGGER.info(
            "Configuration for [%s] upgraded from version [%d] to version [%d]",
            config_entry.title,
            old_version,
            config_entry.version,
        )
    return True


# Track the title of the first entry, it gets the S30.State object
_FIRST_ENTRY_TITLE: str = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup a config entry"""
    _LOGGER.debug(
        "async_setup_entry UniqueID [%s] Data [%s]",
        entry.unique_id,
        dict_redact_fields(entry.data),
    )

    # Determine if this is the first entry that gets S30.State.
    global _FIRST_ENTRY_TITLE
    index: int = 1
    if _FIRST_ENTRY_TITLE is None:
        _FIRST_ENTRY_TITLE = entry.title
    if entry.title == _FIRST_ENTRY_TITLE:
        index = 0

    is_cloud = entry.data[CONF_CLOUD_CONNECTION]

    create_inverter_power: bool = False
    conf_protocol: str = None
    create_diagnostic_sensors: bool = False
    create_parameters: bool = False

    if is_cloud:
        host_name: str = None
        email = entry.data[CONF_EMAIL]
        password = entry.data[CONF_PASSWORD]
    else:
        host_name = entry.data[CONF_HOST]
        email: str = None
        password: str = None
        create_inverter_power: bool = entry.data[CONF_CREATE_INVERTER_POWER]
        create_diagnostic_sensors = entry.data[CONF_CREATE_DIAGNOSTICS_SENSORS]
        create_parameters = entry.data[CONF_CREATE_PARAMETERS]
        conf_protocol: str = entry.data[CONF_PROTOCOL]

    if CONF_APP_ID in entry.data:
        app_id: str = entry.data[CONF_APP_ID]
    else:
        app_id: str = None

    poll_interval = entry.data[CONF_SCAN_INTERVAL]
    fast_poll_interval = entry.data[CONF_FAST_POLL_INTERVAL]
    fast_poll_count = entry.data[CONF_FAST_POLL_COUNT]
    timeout = entry.data[CONF_TIMEOUT]

    allergen_defender_switch = entry.data[CONF_ALLERGEN_DEFENDER_SWITCH]

    conf_init_wait_time = entry.data[CONF_INIT_WAIT_TIME]
    create_sensors = entry.data[CONF_CREATE_SENSORS]
    conf_pii_in_message_logs = entry.data[CONF_PII_IN_MESSAGE_LOGS]
    conf_message_debug_logging = entry.data[CONF_MESSAGE_DEBUG_LOGGING]
    conf_message_debug_file = entry.data[CONF_MESSAGE_DEBUG_FILE]
    # If no path specified then it goes into the config directory,
    if conf_message_debug_file == "":
        conf_message_debug_file = None

    _LOGGER.debug(
        "async_setup starting scan_interval [%s] fast_scan_interval[%s] app_id [%s] config_init_wait_time [%s] create_sensors [%s] create_inverter_power [%s] create_diagnostic_sensors [%s] timeout [%s]",
        poll_interval,
        fast_poll_interval,
        app_id,
        conf_init_wait_time,
        create_sensors,
        create_inverter_power,
        create_diagnostic_sensors,
        timeout,
    )

    manager = Manager(
        hass=hass,
        config=entry,
        email=email,
        password=password,
        poll_interval=poll_interval,
        fast_poll_interval=fast_poll_interval,
        fast_poll_count=fast_poll_count,
        timeout=timeout,
        allergen_defender_switch=allergen_defender_switch,
        app_id=app_id,
        conf_init_wait_time=conf_init_wait_time,
        ip_address=host_name,
        create_sensors=create_sensors,
        create_inverter_power=create_inverter_power,
        protocol=conf_protocol,
        index=index,
        pii_message_logs=conf_pii_in_message_logs,
        message_debug_logging=conf_message_debug_logging,
        message_logging_file=conf_message_debug_file,
        create_diagnostic_sensors=create_diagnostic_sensors,
        create_equipment_parameters=create_parameters,
    )
    try:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, manager.async_shutdown)
        hass.data[DOMAIN][entry.unique_id] = {MANAGER: manager}
        await manager.s30_initialize()
    except S30Exception as err:
        if err.error_code == EC_LOGIN:
            manager.updateState(DS_LOGIN_FAILED)
            raise HomeAssistantError(
                f"Lennox30 unable to login host [{host_name}] - please check credentials and restart Home Assistant"
            ) from err
        elif err.error_code == EC_CONFIG_TIMEOUT:
            _LOGGER.warning("async_setup: %s", err.message)
            _LOGGER.info("connection will be retried in 1 minute")
            asyncio.create_task(manager.initialize_retry_task())
        else:
            _LOGGER.error("async_setup unexpected error %s", err.message)
            _LOGGER.info("connection will be retried in 1 minute")
            asyncio.create_task(manager.initialize_retry_task())
    _LOGGER.debug("async_setup complete host [%s]", host_name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry entry [%s]", entry.unique_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.unique_id)
        manager: Manager = entry_data[MANAGER]
        try:
            await manager.async_shutdown(None)
        except S30Exception as err:
            _LOGGER.error(
                "async_unload_entry entry [%s] error [%s]",
                entry.unique_id,
                err.as_string(),
            )
        except Exception:
            _LOGGER.exception("async_unload_entry entry - unexpected exception [%s]", entry.unique_id)
        return True
    else:
        _LOGGER.error("async_unload_entry call to hass.config_entries.async_unload_platforms returned False")
        return False


class Manager:
    """Manages the connection to cloud or local via API"""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        email: str,
        password: str,
        poll_interval: int,
        fast_poll_interval: float,
        fast_poll_count: int,
        timeout: int,
        allergen_defender_switch: bool,
        app_id: str,
        conf_init_wait_time: int,
        ip_address: str,
        create_sensors: bool,
        create_inverter_power: bool,
        protocol: str,
        index: int = 0,
        pii_message_logs: bool = False,
        message_debug_logging: bool = True,
        message_logging_file: str = None,
        create_diagnostic_sensors: bool = False,
        create_equipment_parameters: bool = False,
    ):
        self.system_parameter_safety_on = {}
        self.config_entry: ConfigEntry = config
        self._reinitialize: bool = False
        self._err_cnt: int = 0
        self.mp_wakeup_event: Event = Event()
        self._climate_entities_initialized: bool = False
        self._hass: HomeAssistant = hass
        self._config: ConfigEntry = config
        self._poll_interval: int = poll_interval
        self._fast_poll_interval: float = fast_poll_interval
        self._fast_poll_count: int = fast_poll_count
        self._protocol = protocol
        self._ip_address = ip_address
        self._pii_message_log = pii_message_logs
        self._message_debug_logging = message_debug_logging
        self._message_logging_file = message_logging_file
        self.api: s30api_async = s30api_async(
            email,
            password,
            app_id,
            ip_address=ip_address,
            protocol=self._protocol,
            pii_message_logs=self._pii_message_log,
            message_debug_logging=self._message_debug_logging,
            message_logging_file=self._message_logging_file,
            timeout=timeout,
        )
        self._shutdown = False
        self._retrieve_task = None
        self.allergen_defender_switch = allergen_defender_switch
        self.create_sensors: bool = create_sensors
        self.create_alert_sensors: bool = True
        self.create_inverter_power: bool = create_inverter_power
        self.create_diagnostic_sensors: bool = create_diagnostic_sensors
        self.create_equipment_parameters: bool = create_equipment_parameters
        self._conf_init_wait_time = conf_init_wait_time
        self._reinitialize = False

        self.is_metric: bool = None
        if self._hass.config.units is US_CUSTOMARY_SYSTEM:
            _LOGGER.info(
                "Manager::init setting units to english - HASS Units [%s]",
                self._hass.config.units._name,
            )
            self.is_metric = False
        else:
            _LOGGER.info(
                "Manager::init setting units to metric - HASS Units [%s]",
                self._hass.config.units._name,
            )
            self.is_metric = True
        self.connected = False
        self.last_cloud_presence_poll: float = None

        self._cs_callbacks = []
        self.system_equip_device_map: dict[str, dict[int, Device]] = {}
        if index == 0:
            self.connection_state = DOMAIN_STATE
        else:
            if ip_address is None:
                e_name = email.split("@")
                redacted_email: str = re.sub("[^A-Za-z0-9]", "_", e_name[0])
                self.connection_state = "lennoxs30.conn_" + redacted_email
            else:
                self.connection_state = "lennoxs30.conn_" + re.sub("[^A-Za-z0-9]", "_", self._ip_address)
            self.connection_state = re.sub("_+", "_", self.connection_state)

    async def async_shutdown(self, event: Event) -> None:
        """Called when hass shutsdown"""
        _LOGGER.debug("async_shutdown started host [%s]", self._ip_address)
        self._shutdown = True
        if self._retrieve_task is not None:
            self.mp_wakeup_event.set()
            await self._retrieve_task
        await self.api.shutdown()
        _LOGGER.debug("async_shutdown complete [%s]", self._ip_address)

    def updateState(self, state: int) -> None:
        """Updates the connection state"""
        if state == DS_CONNECTED and self.connected is False:
            self.connected = True
            self.executeConnectionStateCallbacks()
        elif (
            state
            in (
                DS_RETRY_WAIT,
                DS_LOGIN_FAILED,
            )
            and self.connected
        ):
            self.connected = False
            self.executeConnectionStateCallbacks()
        self._hass.states.async_set(
            self.connection_state, state, self.getMetricsList(), force_update=True, state_info=UNTRACKED_STATE_ATTRIBUTES
        )

    def registerConnectionStateCallback(self, callbackfunc):
        """Register a callback when the connection state changes"""
        self._cs_callbacks.append({"func": callbackfunc})

    def executeConnectionStateCallbacks(self):
        """Executes callbacks when connection state has changed"""
        for callback in self._cs_callbacks:
            callbackfunc = callback["func"]
            try:
                callbackfunc(self.connected)
            except Exception:
                # Log and eat this exception so we can process other callbacks
                _LOGGER.exception("executeConnectionStateCallbacks - failed ")

    def getMetricsList(self):
        """Get the list of connection state metrics"""
        metrics = self.api.metrics.getMetricList()
        # TODO these are at the individual S30 level, when we have a device object we should move this there
        systems = self.api.system_list
        if len(systems) > 0:
            system: lennox_system = self.api.system_list[0]
            if system is not None:
                metrics["sysUpTime"] = system.sysUpTime
                metrics["diagLevel"] = system.diagLevel
                metrics["softwareVersion"] = system.softwareVersion
                metrics["hostname"] = self._ip_address
                metrics["sibling_id"] = {sibling.sibling_identifier for sibling in system.siblings}
                metrics["sibling_ip"] = {sibling.sibling_ipAddress for sibling in system.siblings}
        return metrics

    async def s30_initialize(self):
        """Initialized the connection to the S30"""
        self.updateState(DS_CONNECTING)
        await self.connect_subscribe()
        await self.configuration_initialization()
        if len(g_unique_id_update) != 0:
            await self.unique_id_updates()
        # Launch the message pump loop
        self._retrieve_task = asyncio.create_task(self.messagePump_task())
        # Since there is no change detection implemented to update device attributes like SW version - alwayas reinit
        await self.create_devices()
        # Only add entities the first time, on reconnect we do not need to add them again
        if self._climate_entities_initialized is False:
            await self._hass.config_entries.async_forward_entry_setups(self._config, PLATFORMS)
            self._climate_entities_initialized = True
        self.updateState(DS_CONNECTED)

    async def unique_id_updates(self):
        """Update Unique Ids for affected S40 systems, where the prefix of 123_ was being used"""
        _LOGGER.info("unique_id_updates - checking for affected systems")
        if not self.api.isLANConnection or len(self.api.system_list) != 1:
            return
        system = self.api.system_list[0]
        if system.productType != "S40":
            return

        _LOGGER.info("Updating unique ids for connection [%s]", self.api.ip)
        try:
            await self._update_entity_unique_ids(system)
        except Exception as e:
            _LOGGER.exception(
                "Failed to update entity unique_ids connection [%s] [%s]",
                self.api.ip,
                e,
            )
        try:
            await self._update_device_unique_ids(system)
        except Exception as e:
            _LOGGER.exception(
                "Failed to update device unique_ids connection [%s] [%s]",
                self.api.ip,
                e,
            )

    async def _update_entity_unique_ids(self, system: lennox_system):
        _LOGGER.info("Updating entity unique ids for connection [%s]", self.api.ip)
        ent_reg = er.async_get(self._hass)
        entity_update_list: dict[str, str] = {}
        for regentry in ent_reg.entities.values():
            if regentry.config_entry_id == self.config_entry.entry_id and regentry.platform == LENNOX_DOMAIN:
                if regentry.unique_id.startswith("123_"):
                    suffix = regentry.unique_id.removeprefix("123_")
                    new_unique_id = f"{system.unique_id}_{suffix}".replace("-", "")
                    entity_update_list[regentry.entity_id] = new_unique_id
                    _LOGGER.info(
                        "Updating entity [%s] unique id [%s] new unique id [%s]",
                        regentry.entity_id,
                        regentry.unique_id,
                        new_unique_id,
                    )
        for k, v in entity_update_list.items():
            _LOGGER.info("Committing new entity unique ids for connection [%s] [%s] [%s]", self.api.ip, k, v)
            ent_reg.async_update_entity(k, new_unique_id=v)

    async def _update_device_unique_ids(self, system: lennox_system):
        dev_reg = dr.async_get(self._hass)
        device_update_list: dict[str, str] = {}
        for regentry in dev_reg.devices.values():
            if self.config_entry.entry_id in regentry.config_entries:
                for x in regentry.identifiers:
                    if x[0] == LENNOX_DOMAIN:
                        unique_id = x[1]
                        if unique_id.startswith("123_"):
                            suffix = unique_id.removeprefix("123_")
                            new_unique_id = f"{system.unique_id}_{suffix}"
                            device_update_list[regentry.id] = new_unique_id
                            _LOGGER.info(
                                "Updating device [%s] identifier [%s] new unique id [%s]",
                                regentry.id,
                                unique_id,
                                new_unique_id,
                            )
                        elif unique_id == "123":
                            new_unique_id = system.unique_id
                            device_update_list[regentry.id] = new_unique_id
                            _LOGGER.info(
                                "Updating device [%s] identifier [%s] new unique id [%s]",
                                regentry.id,
                                unique_id,
                                new_unique_id,
                            )
        for k, v in device_update_list.items():
            _LOGGER.info("Committing new device unique ids for connection [%s] [%s] [%s]", self.api.ip, k, v)
            dev_reg.async_update_device(k, new_identifiers={(LENNOX_DOMAIN, v)})

    async def create_devices(self):
        """Creates devices for the discoved lennox equipment"""
        for system in self.api.system_list:
            equip_device_map: dict[int, Device] = self.system_equip_device_map.get(system.sysId)
            if equip_device_map is None:
                equip_device_map = {}
                self.system_equip_device_map[system.sysId] = equip_device_map
            s30: S30ControllerDevice = S30ControllerDevice(self._hass, self.config_entry, system)
            s30.register_device()
            if s30.equipment is not None:
                equip_device_map[s30.equipment.equipment_id] = s30

            if system.has_outdoor_unit:
                s30_outdoor_unit = S30OutdoorUnit(self._hass, self.config_entry, system, s30)
                s30_outdoor_unit.register_device()
                if s30_outdoor_unit.equipment is not None:
                    equip_device_map[s30_outdoor_unit.equipment.equipment_id] = s30_outdoor_unit
            if system.has_indoor_unit:
                s30_indoor_unit = S30IndoorUnit(self._hass, self.config_entry, system, s30)
                s30_indoor_unit.register_device()
                if s30_indoor_unit.equipment is not None:
                    equip_device_map[s30_indoor_unit.equipment.equipment_id] = s30_indoor_unit

            for eq in system.equipment.values():
                if eq.equipment_id != 0 and equip_device_map.get(eq.equipment_id) is None:
                    aux_unit = S30AuxiliaryUnit(self._hass, self.config_entry, system, s30, eq)
                    aux_unit.register_device()
                    equip_device_map[aux_unit.equipment.equipment_id] = aux_unit

            if system.supports_ventilation():
                d: S30VentilationUnit = S30VentilationUnit(self._hass, self.config_entry, system, s30)
                d.register_device()
                equip_device_map[VENTILATION_EQUIPMENT_ID] = d

            for zone in system.zone_list:
                if zone.is_zone_active():
                    if zone.name is None or str(zone.name).strip() == "":
                        fallback_name = helper_create_zone_entity_name(system, zone)
                        _LOGGER.warning(
                            "create_devices active zone missing name host [%s] sysId [%s] zone_id [%s] using fallback [%s]; this usually indicates incomplete zone config message delivery",
                            self._ip_address,
                            system.sysId,
                            zone.id,
                            fallback_name,
                        )
                    z: S30ZoneThermostat = S30ZoneThermostat(self._hass, self.config_entry, system, zone, s30)
                    z.register_device()

            for ble_device in system.ble_devices.values():
                if ble_device.deviceType != "tstat":
                    ble: S40BleDevice = S40BleDevice(self._hass, self.config_entry, system, ble_device, s30)
                    ble.register_device()

    async def initialize_retry_task(self):
        """Retries the connection on failure"""
        while True:
            self.updateState(DS_RETRY_WAIT)
            await asyncio.sleep(RETRY_INTERVAL_SECONDS)
            self.updateState(DS_CONNECTING)
            try:
                await self.s30_initialize()
                self.updateState(DS_CONNECTED)
                return

            except S30Exception as e:
                if e.error_code == EC_LOGIN:
                    # TODO: encapsulate in manager class
                    self.updateState(DS_LOGIN_FAILED)
                    _LOGGER.error(
                        "initialize_retry_task host [%s] %s",
                        self._ip_address,
                        e.as_string(),
                    )
                    return
                elif e.error_code == EC_CONFIG_TIMEOUT:
                    _LOGGER.warning("async_setup: host [%s] %s", self._ip_address, e.as_string())
                    _LOGGER.info(
                        "connection host [%s] will be retried in 1 minute",
                        self._ip_address,
                    )
                else:
                    _LOGGER.error(
                        "async_setup host [%s] unexpected error %s",
                        self._ip_address,
                        e.as_string(),
                    )
                    _LOGGER.info(
                        "async setup host [%s] will be retried in 1 minute",
                        self._ip_address,
                    )

    async def configuration_initialization(self) -> None:
        """Waits for the configuration to arrive"""
        # Wait for zones to appear on each system
        systemsWithZones = 0
        loops: int = 0
        numOfSystems = len(self.api.system_list)
        # To speed startup, we only want to sleep when a message was not received.
        got_message: bool = True
        offline_error_logged = {}
        while systemsWithZones < numOfSystems and loops < self._conf_init_wait_time:
            _LOGGER.debug(
                "configuration_initialization waiting for zone config to arrive host [%s]  numSystems [%d] systemsWithZones [%d]",
                self._ip_address,
                numOfSystems,
                systemsWithZones,
            )
            # Only take a breather if we did not get a message.
            if got_message is False:
                await asyncio.sleep(1.0)
            systemsWithZones = 0
            got_message = await self.messagePump()
            for lsystem in self.api.system_list:
                if lsystem.cloud_status == "offline":
                    if offline_error_logged.get(lsystem.sysId) is None:
                        _LOGGER.error(
                            "The Lennox System with id [%s] is not connected to the Lennox Cloud.  Cloud Status [%s].  Please check your thermostats internet connection and retry.",
                            lsystem.sysId,
                            lsystem.cloud_status,
                        )
                        offline_error_logged[lsystem.sysId] = True
                # Issue #33 - system configuration isn't complete until we've received the name from Lennox.
                if lsystem.config_complete() is False:
                    continue
                numZones = len(lsystem.zone_list)
                numActiveZones = sum(1 for z in lsystem.zone_list if z.is_zone_active())
                numZoneNames = sum(1 for z in lsystem.zone_list if z.is_zone_active() and z.name is not None and str(z.name).strip() != "")
                _LOGGER.debug(
                    "configuration_initialization host [%s] wait for zones system [%s] numZone [%d] activeZones [%d] namedZones [%d]",
                    self._ip_address,
                    lsystem.sysId,
                    numZones,
                    numActiveZones,
                    numZoneNames,
                )
                if numActiveZones > 0 and numZoneNames == numActiveZones:
                    systemsWithZones += 1
            if got_message is False:
                loops += 1
        if systemsWithZones < numOfSystems:
            raise S30Exception(
                "Timeout waiting for configuration data from Lennox - this sometimes happens, the connection will be automatically retried.  Consult the readme for more details",
                EC_CONFIG_TIMEOUT,
                1,
            )

    async def connect(self):
        """Connect to the cloud or local"""
        await self.api.serverConnect()

    async def connect_subscribe(self):
        """Establishes the subscription"""
        await self.api.serverConnect()

        for lsystem in self.api.system_list:
            await self.api.subscribe(lsystem)

    async def reinitialize_task(self) -> None:
        """Reinitializes the connection"""
        while True:
            try:
                self.updateState(DS_CONNECTING)
                _LOGGER.debug("reinitialize_task host [%s] - trying reconnect", self._ip_address)
                await self.connect_subscribe()
                self.updateState(DS_CONNECTED)
                break
            except S30Exception as e:
                _LOGGER.error("reinitialize_task host [%s] %s", self._ip_address, e.as_string())
                if e.error_code == EC_LOGIN:
                    raise HomeAssistantError(
                        f"Lennox30 unable to login host [{self._ip_address}]  - please check credentials and restart Home Assistant"
                    ) from e
            self.updateState(DS_RETRY_WAIT)
            await asyncio.sleep(RETRY_INTERVAL_SECONDS)

        _LOGGER.debug("reinitialize_task host [%s] - reconnect successful", self._ip_address)
        self._retrieve_task = asyncio.create_task(self.messagePump_task())

    async def event_wait_mp_wakeup(self, timeout: float) -> bool:
        """Wakes up the message pump"""
        # suppress TimeoutError because we'll return False in case of timeout
        try:
            await asyncio.wait_for(self.mp_wakeup_event.wait(), timeout)
        except asyncio.TimeoutError:
            return False
        return self.mp_wakeup_event.is_set()

    async def update_cloud_presence(self):
        """Updates the cloud presense"""
        if self.last_cloud_presence_poll is None:
            self.last_cloud_presence_poll = time.time()
            return
        if time.time() - self.last_cloud_presence_poll < 300.0:
            return

        self.last_cloud_presence_poll = time.time()

        for system in self.api.system_list:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("update_cloud_presence sysId [%s]", system.sysId)
            old_status = system.cloud_status
            try:
                await system.update_system_online_cloud()
                new_status = system.cloud_status
                if new_status == "offline" and old_status == "online":
                    _LOGGER.error(
                        "cloud status changed to offline for sysId [%s] name [%s]",
                        system.sysId,
                        system.name,
                    )
                elif old_status == "offline" and new_status == "online":
                    _LOGGER.info(
                        "cloud status changed to online for sysId [%s] name [%s] - resubscribing",
                        system.sysId,
                        system.name,
                    )
                    try:
                        await self.api.subscribe(system)
                    except S30Exception as e:
                        _LOGGER.error(
                            "update_cloud_presence resubscribe error sysid [%s] error %s",
                            system.sysId,
                            e.as_string(),
                        )
                        self._reinitialize = True
                    except Exception as e:
                        _LOGGER.exception(
                            "update_cloud_presence resubscribe error unexpected exception sysid [%s] error {%s}",
                            system.sysId,
                            e,
                        )
                        self._reinitialize = True

            except S30Exception as e:
                _LOGGER.error(
                    "update_cloud_presence sysid [%s] error %s",
                    system.sysId,
                    e.as_string(),
                )
            except Exception as e:
                _LOGGER.exception(
                    "update_cloud_presence unexpected exception sysid [%s] error %s",
                    system.sysId,
                    e,
                )

    def get_reinitialize(self):
        """Determine if object is reinitializing"""
        return self._reinitialize

    async def messagePump_task(self) -> None:
        """Read and process incoming messages"""
        await asyncio.sleep(self._poll_interval)
        self._reinitialize = False
        self._err_cnt = 0
        fast_polling: bool = False
        fast_polling_cd: int = 0
        received = False
        while self.get_reinitialize() is False:
            try:
                received = await self.messagePump()
            except Exception as _:
                _LOGGER.exception("messagePump_task host [%s] unexpected exception", self._ip_address)

            if self.api.isLANConnection is False:
                await self.update_cloud_presence()

            if fast_polling:
                fast_polling_cd = fast_polling_cd - 1
                if fast_polling_cd <= 0:
                    fast_polling = False

            if self._shutdown:
                break

            if not received:
                if fast_polling:
                    res = await asyncio.sleep(min(self._fast_poll_interval, self._poll_interval))
                else:
                    res = await self.event_wait_mp_wakeup(self._poll_interval)
                    if res:
                        self.mp_wakeup_event.clear()
                        fast_polling = True
                        fast_polling_cd = self._fast_poll_count

        if self._shutdown:
            _LOGGER.debug("messagePump_task host [%s] is exiting to shutdown", self._ip_address)
            return
        elif self.get_reinitialize():
            self.updateState(DS_DISCONNECTED)
            asyncio.create_task(self.reinitialize_task())
            _LOGGER.debug(
                "messagePump_task host [%s] is exiting - to enter retries",
                self._ip_address,
            )
        else:
            _LOGGER.error(
                "messagePump_task host [%s] is exiting - and this should not happen",
                self._ip_address,
            )

    async def messagePump(self) -> bool:
        """Read and process a message"""
        bErr = False
        received = False
        try:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("messagePump host [%s] running", self._ip_address)
            received = await self.api.messagePump()
            self.updateState(DS_CONNECTED)
        except S30Exception as e:
            self._err_cnt += 1
            # This should mean we have been logged out and need to start the login process
            if e.error_code == EC_UNAUTHORIZED:
                _LOGGER.warning(
                    "messagePump host [%s] - unauthorized - trying to relogin",
                    self._ip_address,
                )
                self._reinitialize = True
            # If its an HTTP error, we will not log an error, just and info message, unless
            # this exceeds the max consecutive error count
            elif e.error_code == EC_HTTP_ERR and self._err_cnt < MAX_ERRORS:
                _LOGGER.debug(
                    "messagePump http error host [%s] %s",
                    self._ip_address,
                    e.as_string(),
                )
            # Since the S30 will close connections and kill the subscription periodically, these errors
            # are expected.  Log as warnings
            elif e.error_code == EC_COMMS_ERROR:
                _LOGGER.warning(
                    "messagePump communication error host [%s] %s",
                    self._ip_address,
                    e.as_string(),
                )
            else:
                _LOGGER.warning("messagePump error host [%s] %s", self._ip_address, e.as_string())
            bErr = True
        except Exception:
            _LOGGER.exception("messagePump unexpected exception host [%s]", self._ip_address)
            self._err_cnt += 1
            bErr = True
        # Keep retrying retrive up until we get this number of errors in a row, at which point will try to reconnect
        if self._err_cnt >= MAX_ERRORS:
            _LOGGER.info(
                "messagePump encountered [%d] consecutive errors host [%s] - reinitializing connection",
                self._err_cnt,
                self._ip_address,
            )
            self._reinitialize = True
        if bErr is False:
            self._err_cnt = 0
        return received

    def parameter_safety_on(self, sysId: str) -> bool:
        """Turn parameter safety on"""
        return self.system_parameter_safety_on.get(sysId, False)

    def parameter_safety_turn_on(self, sysId: str) -> None:
        """Turn parameter safety on"""
        self.system_parameter_safety_on[sysId] = True

    def parameter_safety_turn_off(self, sysId: str) -> None:
        """Turns parameter safety off"""
        self.system_parameter_safety_on[sysId] = False
