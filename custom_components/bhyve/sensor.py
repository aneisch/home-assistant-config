"""Support for Orbit BHyve sensors."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.icon import icon_for_battery_level

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
from .pybhyve.client import BHyveClient
from .pybhyve.errors import BHyveError
from .pybhyve.typings import BHyveDevice
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
            all_zones = device.get("zones")
            for zone in all_zones:
                # if the zone doesn't have a name, set it to the device's name if
                # there is only one (eg a hose timer)
                zone_name = zone.get("name", None)
                if zone_name is None:
                    zone_name = (
                        device.get("name") if len(all_zones) == 1 else "Unnamed Zone"
                    )
                sensors.append(
                    BHyveZoneHistorySensor(hass, bhyve, device, zone, zone_name)
                )

            if device.get("battery", None) is not None:
                sensors.append(BHyveBatterySensor(hass, bhyve, device))
        if device.get("type") == DEVICE_FLOOD:
            sensors.append(BHyveTemperatureSensor(hass, bhyve, device))
            sensors.append(BHyveBatterySensor(hass, bhyve, device))

    async_add_entities(sensors)


class BHyveBatterySensor(BHyveDeviceEntity, SensorEntity):
    """Define a BHyve sensor."""

    _state: int | None = None

    def __init__(
        self, hass: HomeAssistant, bhyve: BHyveClient, device: BHyveDevice
    ) -> None:
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

        self._state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _setup(self, device: Any) -> None:
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
    def state(self) -> int | None:
        """Return the state of the entity."""
        return self._state

    @property
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        if self._state is not None:
            return icon_for_battery_level(
                battery_level=int(self._state), charging=False
            )
        return self._icon

    @property
    def should_poll(self) -> bool:
        """Enable polling."""
        return True

    @property
    def scan_interval(self) -> timedelta:
        """Return the scan interval."""
        return SCAN_INTERVAL

    @property
    def unique_id(self) -> str:
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:battery"

    def _should_handle_event(self, event_name: str, _data: dict) -> bool:
        return event_name in [EVENT_BATTERY_STATUS, EVENT_CHANGE_MODE]

    def _on_ws_data(self, data: dict) -> None:
        # {'event': 'battery_status', 'mv': 3311, 'charging': false ... }
        #
        event: str = data.get("event", "")
        if event in (EVENT_BATTERY_STATUS):
            battery_level = self.parse_battery_level(data)

            self._state = battery_level
            self._attrs[ATTR_BATTERY_LEVEL] = battery_level

    async def async_update(self) -> None:
        """Retrieve latest state."""
        await super().async_update()
        await self._refetch_device()

    @staticmethod
    def parse_battery_level(battery_data: dict) -> int:
        """
        Parses the battery level data and returns the battery level as a percentage.

        If the 'percent' attribute is present in the battery data, it is used as the battery level.
        Otherwise, if the 'mv' attribute is present, the battery level is calculated as a percentage
        based on the millivolts, assuming that 2x1.5V AA batteries are used. Note that AA batteries can
        range from 1.2V to 1.7V depending on their chemistry, so the calculation may not be accurate
        for all types of batteries. YMMV

        Args:
        ----
        battery_data (dict): A dictionary containing the battery data.

        Returns:
        -------
        float: The battery level as a percentage.

        """  # noqa: D401, E501
        if not isinstance(battery_data, dict):
            _LOGGER.warning("Unexpected battery data, returning 0: %s", battery_data)
            return 0

        battery_level = battery_data.get("percent", 0)
        if "mv" in battery_data and "percent" not in battery_data:
            battery_level = min(battery_data.get("mv", 0) / 3000 * 100, 100)
        return battery_level


class BHyveZoneHistorySensor(BHyveDeviceEntity):
    """Define a BHyve sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        bhyve: BHyveClient,
        device: BHyveDevice,
        zone: dict,
        zone_name: str,
    ) -> None:
        """Initialize the sensor."""
        self._history = None
        self._zone = zone
        self._zone_id = zone.get("station")

        name = f"{zone_name} zone history"
        _LOGGER.info("Creating history sensor: %s", name)

        super().__init__(
            hass,
            bhyve,
            device,
            name,
            "history",
            SensorDeviceClass.TIMESTAMP,
        )

    def _setup(self, device: BHyveDevice) -> None:
        self._state = None
        self._attrs = {}
        self._available = device.get("is_connected", False)

    @property
    def state(self) -> str | None:
        """Return the state of the entity."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Enable polling."""
        return True

    @property
    def unique_id(self) -> str:
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:{self._zone_id}:history"

    @property
    def entity_category(self) -> EntityCategory:
        """History is a diagnostic category."""
        return EntityCategory.DIAGNOSTIC

    def _should_handle_event(self, event_name: str, _data: dict) -> bool:
        return event_name in [EVENT_DEVICE_IDLE]

    async def async_update(self) -> None:
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

    _state: str

    def __init__(
        self, hass: HomeAssistant, bhyve: BHyveClient, device: BHyveDevice
    ) -> None:
        """Initialize the sensor."""
        name = "{} state".format(device.get("name"))
        _LOGGER.info("Creating state sensor: %s", name)
        super().__init__(hass, bhyve, device, name, "information")

    def _setup(self, device: BHyveDevice) -> None:
        self._attrs = {}
        self._state = device.get("status", {}).get("run_mode", "unavailable")
        self._available = device.get("is_connected", False)
        _LOGGER.debug(
            "State sensor %s setup: State: %s | Available: %s",
            self._name,
            self._state,
            self._available,
        )

    @property
    def state(self) -> str:
        """Return the state of the entity."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:state"

    @property
    def entity_category(self) -> EntityCategory:
        """Run state is a diagnostic category."""
        return EntityCategory.DIAGNOSTIC

    def _on_ws_data(self, data: dict) -> None:
        #
        # {'event': 'change_mode', 'mode': 'auto', 'device_id': 'id', 'timestamp': '2020-01-09T20:30:00.000Z'}  # noqa: E501, ERA001
        #
        event = data.get("event")
        if event == EVENT_CHANGE_MODE:
            self._state = data.get("mode", "unavailable")

    def _should_handle_event(self, event_name: str, _data: dict) -> bool:
        return event_name in [EVENT_CHANGE_MODE]


class BHyveTemperatureSensor(BHyveDeviceEntity, SensorEntity):
    """Define a BHyve sensor."""

    def __init__(
        self, hass: HomeAssistant, bhyve: BHyveClient, device: BHyveDevice
    ) -> None:
        """Initialize the sensor."""
        name = "{} temperature sensor".format(device.get("name"))
        _LOGGER.info("Creating temperature sensor: %s", name)
        super().__init__(
            hass, bhyve, device, name, "thermometer", SensorDeviceClass.TEMPERATURE
        )

    def _setup(self, device: BHyveDevice) -> None:
        self._available = device.get("is_connected", False)
        self._attr_native_value = device.get("status", {}).get("temp_f")
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._state_class = SensorStateClass.MEASUREMENT

        self._attrs = {
            "location": device.get("location_name"),
            "rssi": device.get("status", {}).get("rssi"),
            "temperature_alarm": device.get("status", {}).get("temp_alarm_status"),
        }
        _LOGGER.debug(
            "Temperature sensor %s setup: Value: %s | Available: %s",
            self._name,
            self._attr_native_value,
            self._available,
        )

    @property
    def unique_id(self) -> str:
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:temp"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._attr_native_value is not None

    def _on_ws_data(self, data: dict) -> None:
        #
        # {"last_flood_alarm_at":"2021-08-29T16:32:35.585Z","rssi":-60,"onboard_complete":true,"temp_f":75.2,"provisioned":true,"phy":"le_1m_1000","event":"fs_status_update","temp_alarm_status":"ok","status_updated_at":"2021-08-29T16:33:17.089Z","identify_enabled":false,"device_id":"612ad9134f0c6c9c9faddbba","timestamp":"2021-08-29T16:33:17.089Z","flood_alarm_status":"ok","last_temp_alarm_at":null}  # noqa: E501, ERA001
        #
        _LOGGER.info("Received program data update %s", data)
        event = data.get("event")
        if event == EVENT_FS_ALARM:
            temp = data.get("temp_f")
            self._attr_native_value = float(temp) if temp is not None else None
            self._attrs["rssi"] = data.get("rssi")
            self._attrs["temperature_alarm"] = data.get("temp_alarm_status")

    def _should_handle_event(self, event_name: str, _data: dict) -> bool:
        return event_name in [EVENT_FS_ALARM]
