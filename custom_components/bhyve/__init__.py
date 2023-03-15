"""Support for Orbit BHyve irrigation devices."""
import logging
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_PROGRAM_CHANGED,
    EVENT_RAIN_DELAY,
    EVENT_SET_MANUAL_PRESET_TIME,
    MANUFACTURER,
    SIGNAL_UPDATE_DEVICE,
    SIGNAL_UPDATE_PROGRAM,
)
from .util import filter_configured_devices
from .pybhyve import Client
from .pybhyve.errors import AuthenticationError, BHyveError

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    cv.deprecated(DOMAIN),
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the BHyve component from YAML."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BHyve from a config entry."""

    async def async_update_callback(data):
        event = data.get("event")
        device_id = None
        program_id = None

        if event == EVENT_PROGRAM_CHANGED:
            device_id = data.get("program", {}).get("device_id")
            program_id = data.get("program", {}).get("id")
        else:
            device_id = data.get("device_id")

        if device_id is not None:
            async_dispatcher_send(
                hass, SIGNAL_UPDATE_DEVICE.format(device_id), device_id, data
            )
        if program_id is not None:
            async_dispatcher_send(
                hass, SIGNAL_UPDATE_PROGRAM.format(program_id), program_id, data
            )

    client = Client(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )

    try:
        if await client.login() is False:
            raise ConfigEntryAuthFailed()

        client.listen(hass.loop, async_update_callback)
        all_devices = await client.devices
        programs = await client.timer_programs
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed() from err
    except BHyveError as err:
        raise ConfigEntryNotReady() from err

    # Filter the device list to those that are enabled in options
    devices = filter_configured_devices(entry, all_devices)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "devices": devices,
        "programs": programs,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, client.stop())

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload to update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class BHyveEntity(Entity):
    """Define a base BHyve entity."""

    def __init__(
        self,
        hass,
        bhyve,
        device,
        name,
        icon,
        device_class=None,
    ):
        """Initialize the sensor."""
        self._hass = hass
        self._bhyve: Client = bhyve
        self._device_class = device_class

        self._name = name
        self._icon = f"mdi:{icon}"
        self._state = None
        self._available = False
        self._attrs = {}

        self._device_id = device.get("id")
        self._device_type = device.get("type")
        self._device_name = device.get("name")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            configuration_url=f"https://techsupport.orbitbhyve.com/dashboard/support/device/{self._device_id}",
            name=self._device_name,
            model=device.get("hardware_version"),
            hw_version=device.get("hardware_version"),
            sw_version=device.get("firmware_version"),
        )

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        return self._attrs

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def should_poll(self):
        """Disable polling."""
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return self._attr_device_info


class BHyveWebsocketEntity(BHyveEntity):
    """An entity which responds to websocket events."""

    def __init__(
        self,
        hass,
        bhyve,
        device,
        name,
        icon,
        device_class=None,
    ):
        self._async_unsub_dispatcher_connect = None
        self._ws_unprocessed_events = []
        super().__init__(hass, bhyve, device, name, icon, device_class)

    def _on_ws_data(self, data):
        pass

    def _should_handle_event(self, event_name, data):
        """True if the websocket event should be handled."""
        return True

    async def async_update(self):
        """Retrieve latest state."""
        ws_updates = list(self._ws_unprocessed_events)
        self._ws_unprocessed_events[:] = []

        for ws_event in ws_updates:
            self._on_ws_data(ws_event)


class BHyveDeviceEntity(BHyveWebsocketEntity):
    """Define a base BHyve entity with a device."""

    def __init__(
        self,
        hass,
        bhyve,
        device,
        name,
        icon,
        device_class=None,
    ):
        """Initialize the sensor."""

        self._mac_address = device.get("mac_address")

        super().__init__(hass, bhyve, device, name, icon, device_class)

        self._setup(device)

    def _setup(self, device):
        pass

    async def _refetch_device(self, force_update=False):
        try:
            device = await self._bhyve.get_device(self._device_id, force_update)
            if not device:
                _LOGGER.info("No device found with id %s", self._device_id)
                self._available = False
                return

            self._setup(device)

        except BHyveError as err:
            _LOGGER.warning("Unable to retreive data for %s: %s", self.name, err)

    async def _fetch_device_history(self, force_update=False):
        try:
            return await self._bhyve.get_device_history(self._device_id, force_update)

        except BHyveError as err:
            raise (err)

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        raise HomeAssistantError(
            f"{self.__class__.__name__} does not define a unique_id"
        )

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update(device_id, data):
            """Update the state."""
            event = data.get("event")
            if event == "device_disconnected":
                _LOGGER.warning(
                    "Device %s disconnected and is no longer available", self.name
                )
                self._available = False
            elif event == "device_connected":
                _LOGGER.info("Device %s reconnected and is now available", self.name)
                self._available = True
            if self._should_handle_event(event, data):
                _LOGGER.info(
                    "Message received: %s - %s - %s",
                    self.name,
                    self._device_id,
                    str(data),
                )
                self._ws_unprocessed_events.append(data)
                self.async_schedule_update_ha_state(True)

        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_DEVICE.format(self._device_id), update
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()

    async def set_manual_preset_runtime(self, minutes: int):
        """Sets the default watering runtime for the device."""
        # {event: "set_manual_preset_runtime", device_id: "abc", seconds: 900}
        payload = {
            "event": EVENT_SET_MANUAL_PRESET_TIME,
            "device_id": self._device_id,
            "seconds": minutes * 60,
        }
        _LOGGER.info("Setting manual preset runtime: %s", payload)
        await self._bhyve.send_message(payload)

    async def enable_rain_delay(self, hours: int = 24):
        """Enable rain delay."""
        await self._set_rain_delay(hours)

    async def disable_rain_delay(self):
        """Disable rain delay."""
        await self._set_rain_delay(0)

    async def _set_rain_delay(self, hours: int):
        try:
            # {event: "rain_delay", device_id: "abc", delay: 48}
            payload = {
                "event": EVENT_RAIN_DELAY,
                "device_id": self._device_id,
                "delay": hours,
            }
            _LOGGER.info("Setting rain delay: %s", payload)
            await self._bhyve.send_message(payload)

        except BHyveError as err:
            _LOGGER.warning("Failed to send to BHyve websocket message %s", err)
            raise (err)
