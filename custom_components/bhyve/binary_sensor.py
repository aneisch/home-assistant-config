"""Support for Orbit BHyve sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BHyveDeviceEntity
from .const import CONF_CLIENT, DEVICE_FLOOD, DOMAIN, EVENT_FS_ALARM
from .util import filter_configured_devices

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve binary sensor platform from a config entry."""

    bhyve = hass.data[DOMAIN][entry.entry_id][CONF_CLIENT]

    sensors = []

    # Filter the device list to those that are enabled in options
    devices = filter_configured_devices(entry, await bhyve.devices)

    for device in devices:
        if device.get("type") == DEVICE_FLOOD:
            sensors.append(BHyveFloodSensor(hass, bhyve, device))
            sensors.append(BHyveTemperatureBinarySensor(hass, bhyve, device))

    async_add_entities(sensors, True)


class BHyveFloodSensor(BHyveDeviceEntity):
    """Define a BHyve flood sensor."""

    def __init__(self, hass, bhyve, device):
        """Initialize the sensor."""
        name = "{} flood sensor".format(device.get("name"))
        _LOGGER.info("Creating flood sensor: %s", name)
        super().__init__(
            hass, bhyve, device, name, "water", BinarySensorDeviceClass.MOISTURE
        )

    def _setup(self, device):
        self._available = device.get("is_connected", False)
        self._state = self._parse_status(device.get("status", {}))
        self._attrs = {
            "location": device.get("location_name"),
            "shutoff": device.get("auto_shutoff"),
            "rssi": device.get("status", {}).get("rssi"),
        }
        _LOGGER.debug(
            "Flood sensor %s setup: State: %s | Available: %s",
            self._name,
            self._state,
            self._available,
        )

    def _parse_status(self, status):
        """Convert BHyve alarm status to entity value."""
        return "on" if status.get("flood_alarm_status") == "alarm" else "off"

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._mac_address}:{self._device_id}:water"

    @property
    def is_on(self):
        """Reports state of the flood sensor."""
        return self._state == "on"

    def _on_ws_data(self, data):
        """
        {"last_flood_alarm_at":"2021-08-29T16:32:35.585Z","rssi":-60,"onboard_complete":true,"temp_f":75.2,"provisioned":true,"phy":"le_1m_1000","event":"fs_status_update","temp_alarm_status":"ok","status_updated_at":"2021-08-29T16:33:17.089Z","identify_enabled":false,"device_id":"612ad9134f0c6c9c9faddbba","timestamp":"2021-08-29T16:33:17.089Z","flood_alarm_status":"ok","last_temp_alarm_at":null}
        """
        _LOGGER.info("Received program data update %s", data)
        event = data.get("event")
        if event == EVENT_FS_ALARM:
            self._state = self._parse_status(data)
            self._attrs["rssi"] = data.get("rssi")

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_FS_ALARM]


class BHyveTemperatureBinarySensor(BHyveDeviceEntity):
    """Define a BHyve temperature sensor."""

    def __init__(self, hass, bhyve, device):
        name = "{} temperature alert".format(device.get("name"))
        super().__init__(hass, bhyve, device, name, "alert")

    def _setup(self, device):
        self._available = device.get("is_connected", False)
        self._state = self._parse_status(device.get("status", {}))
        self._attrs = device.get("temp_alarm_thresholds")

    def _parse_status(self, status):
        """Convert BHyve alarm status to entity value."""
        return "on" if "alarm" in status.get("temp_alarm_status") else "off"

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._mac_address}:{self._device_id}:tempalert"

    @property
    def is_on(self):
        """Reports state of the temperature sensor."""
        return self._state == "on"

    def _on_ws_data(self, data):
        _LOGGER.info("Received program data update %s", data)
        event = data.get("event")
        if event == EVENT_FS_ALARM:
            self._state = self._parse_status(data)

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_FS_ALARM]
