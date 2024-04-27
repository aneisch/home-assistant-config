"""Support for Orbit BHyve sensors."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_BATTERY_LEVEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.icon import icon_for_battery_level

from homeassistant.components.sensor import SensorDeviceClass

from . import BHyveDeviceEntity
from .const import (
    CONF_CLIENT,
    DEVICE_FLOOD,
    DEVICE_SPRINKLER,
    DOMAIN,
    EVENT_BATTERY_STATUS,
    EVENT_CHANGE_MODE,
    EVENT_DEVICE_IDLE,
    EVENT_FS_ALARM,
)
from .pybhyve.errors import BHyveError
from .util import filter_configured_devices, orbit_time_to_local_time

_LOGGER = logging.getLogger(__name__)

ATTR_BUDGET = "budget"
ATTR_CONSUMPTION_GALLONS = "consumption_gallons"
ATTR_CONSUMPTION_LITRES = "consumption_litres"
ATTR_IRRIGATION = "irrigation"
ATTR_PROGRAM = "program"
ATTR_PROGRAM_NAME = "program_name"
ATTR_RUN_TIME = "run_time"
ATTR_START_TIME = "start_time"
ATTR_STATUS = "status"

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve sensor platform from a config entry."""

    bhyve = hass.data[DOMAIN][entry.entry_id][CONF_CLIENT]

    sensors = []
    devices = filter_configured_devices(entry, await bhyve.devices)

    for device in devices:
        if device.get("type") == DEVICE_SPRINKLER:
            sensors.append(BHyveStateSensor(hass, bhyve, device))
            for zone in device.get("zones"):
                sensors.append(BHyveZoneHistorySensor(hass, bhyve, device, zone))

            if device.get("battery", None) is not None:
                sensors.append(BHyveBatterySensor(hass, bhyve, device))
        if device.get("type") == DEVICE_FLOOD:
            sensors.append(BHyveTemperatureSensor(hass, bhyve, device))
            sensors.append(BHyveBatterySensor(hass, bhyve, device))

    async_add_entities(sensors)


class BHyveBatterySensor(BHyveDeviceEntity):
    """Define a BHyve sensor."""

    def __init__(self, hass, bhyve, device):
        """Initialize the sensor."""
        name = "{} battery level".format(device.get("name"))
        _LOGGER.info("Creating battery sensor: %s", name)
        super().__init__(
            hass,
            bhyve,
            device,
            name,
            "battery",
            SensorDeviceClass.BATTERY,
        )

        self._unit = "%"

    def _setup(self, device):
        self._state = None
        self._attrs = {}
        self._available = device.get("is_connected", False)

        battery = device.get("battery")

        _LOGGER.debug("%s battery: %s", self._device_name, battery)

        if battery is not None:
            battery_level = self.parse_battery_level(battery)

            self._state = battery_level
            self._attrs[ATTR_BATTERY_LEVEL] = battery_level

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return self._unit

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._device_class == SensorDeviceClass.BATTERY and self._state is not None:
            return icon_for_battery_level(
                battery_level=int(self._state), charging=False
            )
        return self._icon

    @property
    def should_poll(self):
        """Enable polling."""
        return True

    @property
    def scan_interval(self):
        """Return the scan interval."""
        return SCAN_INTERVAL

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:battery"

    @property
    def entity_category(self):
        """Battery is a diagnostic category."""
        return EntityCategory.DIAGNOSTIC

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_BATTERY_STATUS, EVENT_CHANGE_MODE]

    def _on_ws_data(self, data):
        # {'event': 'battery_status', 'mv': 3311, 'charging': false ... }
        #
        event = data.get("event")
        if event in (EVENT_BATTERY_STATUS):
            battery_level = self.parse_battery_level(data)

            self._state = battery_level
            self._attrs[ATTR_BATTERY_LEVEL] = battery_level

    async def async_update(self):
        """Retrieve latest state."""
        await super().async_update()
        await self._refetch_device()

    @staticmethod
    def parse_battery_level(battery_data):
        """
        Parses the battery level data and returns the battery level as a percentage.

        If the 'percent' attribute is present in the battery data, it is used as the battery level.
        Otherwise, if the 'mv' attribute is present, the battery level is calculated as a percentage
        based on the millivolts, assuming that 2x1.5V AA batteries are used. Note that AA batteries can
        range from 1.2V to 1.7V depending on their chemistry, so the calculation may not be accurate
        for all types of batteries. YMMV ¯\_(ツ)_/¯

        Args:
        battery_data (dict): A dictionary containing the battery data.

        Returns:
        float: The battery level as a percentage.
        """

        if not isinstance(battery_data, dict):
            _LOGGER.warning("Unexpected battery data, returning 0: %s", battery_data)
            return 0

        battery_level = battery_data.get("percent", 0)
        if "mv" in battery_data and "percent" not in battery_data:
            battery_level = min(battery_data.get("mv", 0) / 3000 * 100, 100)
        return battery_level


class BHyveZoneHistorySensor(BHyveDeviceEntity):
    """Define a BHyve sensor."""

    def __init__(self, hass, bhyve, device, zone):
        """Initialize the sensor."""
        self._history = None
        self._zone = zone
        self._zone_id = zone.get("station")

        name = "{} zone history".format(zone.get("name", "Unknown"))
        _LOGGER.info("Creating history sensor: %s", name)

        super().__init__(
            hass,
            bhyve,
            device,
            name,
            "history",
            SensorDeviceClass.TIMESTAMP,
        )

    def _setup(self, device):
        self._state = None
        self._attrs = {}
        self._available = device.get("is_connected", False)

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def should_poll(self):
        """Enable polling."""
        return True

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:{self._zone_id}:history"

    @property
    def entity_category(self):
        """History is a diagnostic category."""
        return EntityCategory.DIAGNOSTIC

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_DEVICE_IDLE]

    async def async_update(self):
        """Retrieve latest state."""
        force_update = bool(list(self._ws_unprocessed_events))
        self._ws_unprocessed_events[:] = []  # We don't care about these

        try:
            history = await self._fetch_device_history(force_update=force_update) or []
            self._history = history

            for history_item in history:
                zone_irrigation = list(
                    filter(
                        lambda i: i.get("station") == self._zone_id,
                        history_item.get(ATTR_IRRIGATION, []),
                    )
                )
                if zone_irrigation:
                    # This is a bit crude - assumes the list is ordered by time.
                    latest_irrigation = zone_irrigation[-1]

                    gallons = latest_irrigation.get("water_volume_gal")
                    litres = round(gallons * 3.785, 2) if gallons else None

                    self._state = orbit_time_to_local_time(
                        latest_irrigation.get("start_time")
                    ).isoformat()

                    self._attrs = {
                        ATTR_BUDGET: latest_irrigation.get(ATTR_BUDGET),
                        ATTR_PROGRAM: latest_irrigation.get(ATTR_PROGRAM),
                        ATTR_PROGRAM_NAME: latest_irrigation.get(ATTR_PROGRAM_NAME),
                        ATTR_RUN_TIME: latest_irrigation.get(ATTR_RUN_TIME),
                        ATTR_STATUS: latest_irrigation.get(ATTR_STATUS),
                        ATTR_CONSUMPTION_GALLONS: gallons,
                        ATTR_CONSUMPTION_LITRES: litres,
                        ATTR_START_TIME: latest_irrigation.get(ATTR_START_TIME),
                    }
                    break

        except BHyveError as err:
            _LOGGER.warning("Unable to retreive data for %s: %s", self._name, err)


class BHyveStateSensor(BHyveDeviceEntity):
    """Define a BHyve sensor."""

    def __init__(self, hass, bhyve, device):
        """Initialize the sensor."""
        name = "{} state".format(device.get("name"))
        _LOGGER.info("Creating state sensor: %s", name)
        super().__init__(hass, bhyve, device, name, "information")

    def _setup(self, device):
        self._attrs = {}
        self._state = device.get("status", {}).get("run_mode")
        self._available = device.get("is_connected", False)
        _LOGGER.debug(
            "State sensor %s setup: State: %s | Available: %s",
            self._name,
            self._state,
            self._available,
        )

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:state"

    @property
    def entity_category(self):
        """Run state is a diagnostic category."""
        return EntityCategory.DIAGNOSTIC

    def _on_ws_data(self, data):
        #
        # {'event': 'change_mode', 'mode': 'auto', 'device_id': 'id', 'timestamp': '2020-01-09T20:30:00.000Z'}
        #
        event = data.get("event")
        if event == EVENT_CHANGE_MODE:
            self._state = data.get("mode")

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_CHANGE_MODE]


class BHyveTemperatureSensor(BHyveDeviceEntity):
    """Define a BHyve sensor."""

    def __init__(self, hass, bhyve, device):
        """Initialize the sensor."""
        name = "{} temperature sensor".format(device.get("name"))
        _LOGGER.info("Creating temperature sensor: %s", name)
        super().__init__(
            hass, bhyve, device, name, "thermometer", SensorDeviceClass.TEMPERATURE
        )

    def _setup(self, device):
        self._state = device.get("status", {}).get("temp_f")
        self._available = device.get("is_connected", False)
        self._unit = "°F"
        self._attrs = {
            "location": device.get("location_name"),
            "rssi": device.get("status", {}).get("rssi"),
            "temperature_alarm": device.get("status", {}).get("temp_alarm_status"),
        }
        _LOGGER.debug(
            "Temperature sensor %s setup: State: %s | Available: %s",
            self._name,
            self._state,
            self._available,
        )

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return self._unit

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:temp"

    def _on_ws_data(self, data):
        #
        # {"last_flood_alarm_at":"2021-08-29T16:32:35.585Z","rssi":-60,"onboard_complete":true,"temp_f":75.2,"provisioned":true,"phy":"le_1m_1000","event":"fs_status_update","temp_alarm_status":"ok","status_updated_at":"2021-08-29T16:33:17.089Z","identify_enabled":false,"device_id":"612ad9134f0c6c9c9faddbba","timestamp":"2021-08-29T16:33:17.089Z","flood_alarm_status":"ok","last_temp_alarm_at":null}
        #
        _LOGGER.info("Received program data update %s", data)
        event = data.get("event")
        if event == EVENT_FS_ALARM:
            self._state = data.get("temp_f")
            self._attrs["rssi"] = data.get("rssi")
            self._attrs["temperature_alarm"] = data.get("temp_alarm_status")

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_FS_ALARM]
