"""Support for Orbit BHyve switch (toggle zone)."""
import datetime
from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt

from . import BHyveDeviceEntity, BHyveWebsocketEntity
from .const import (
    CONF_CLIENT,
    DEVICE_SPRINKLER,
    DOMAIN,
    EVENT_CHANGE_MODE,
    EVENT_DEVICE_IDLE,
    EVENT_PROGRAM_CHANGED,
    EVENT_RAIN_DELAY,
    EVENT_SET_MANUAL_PRESET_TIME,
    EVENT_WATERING_COMPLETE,
    EVENT_WATERING_IN_PROGRESS,
    SIGNAL_UPDATE_PROGRAM,
)
from .pybhyve.errors import BHyveError
from .util import filter_configured_devices, orbit_time_to_local_time

_LOGGER = logging.getLogger(__name__)

DEFAULT_MANUAL_RUNTIME = timedelta(minutes=5)

PROGRAM_SMART_WATERING = "e"
PROGRAM_MANUAL = "manual"

ATTR_MANUAL_RUNTIME = "manual_preset_runtime"
ATTR_SMART_WATERING_ENABLED = "smart_watering_enabled"
ATTR_SPRINKLER_TYPE = "sprinkler_type"
ATTR_IMAGE_URL = "image_url"
ATTR_STARTED_WATERING_AT = "started_watering_station_at"
ATTR_SMART_WATERING_PLAN = "watering_program"
ATTR_CURRENT_STATION = "current_station"
ATTR_CURRENT_PROGRAM = "current_program"
ATTR_CURRENT_RUNTIME = "current_runtime"
ATTR_NEXT_START_TIME = "next_start_time"
ATTR_NEXT_START_PROGRAMS = "next_start_programs"

# Service Attributes
ATTR_MINUTES = "minutes"
ATTR_HOURS = "hours"
ATTR_PERCENTAGE = "percentage"

# Rain Delay Attributes
ATTR_CAUSE = "cause"
ATTR_DELAY = "delay"
ATTR_WEATHER_TYPE = "weather_type"
ATTR_STARTED_AT = "started_at"

ATTR_PROGRAM = "program_{}"

SERVICE_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    }
)

ENABLE_RAIN_DELAY_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_HOURS): cv.positive_int,
    }
)

START_WATERING_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_MINUTES): cv.positive_int,
    }
)

SET_PRESET_RUNTIME_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_MINUTES): cv.positive_int,
    }
)

SET_SMART_WATERING_SOIL_MOISTURE_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_PERCENTAGE): cv.positive_int,
    }
)

SERVICE_ENABLE_RAIN_DELAY = "enable_rain_delay"
SERVICE_DISABLE_RAIN_DELAY = "disable_rain_delay"
SERVICE_START_WATERING = "start_watering"
SERVICE_STOP_WATERING = "stop_watering"
SERVICE_SET_MANUAL_PRESET_RUNTIME = "set_manual_preset_runtime"
SERVICE_SET_SMART_WATERING_SOIL_MOISTURE = "set_smart_watering_soil_moisture"
SERVICE_START_PROGRAM = "start_program"


SERVICE_TO_METHOD = {
    SERVICE_ENABLE_RAIN_DELAY: {
        "method": "enable_rain_delay",
        "schema": ENABLE_RAIN_DELAY_SCHEMA,
    },
    SERVICE_DISABLE_RAIN_DELAY: {
        "method": "disable_rain_delay",
        "schema": SERVICE_BASE_SCHEMA,
    },
    SERVICE_START_WATERING: {
        "method": "start_watering",
        "schema": START_WATERING_SCHEMA,
    },
    SERVICE_STOP_WATERING: {"method": "stop_watering", "schema": SERVICE_BASE_SCHEMA},
    SERVICE_SET_MANUAL_PRESET_RUNTIME: {
        "method": "set_manual_preset_runtime",
        "schema": SET_PRESET_RUNTIME_SCHEMA,
    },
    SERVICE_SET_SMART_WATERING_SOIL_MOISTURE: {
        "method": "set_smart_watering_soil_moisture",
        "schema": SET_SMART_WATERING_SOIL_MOISTURE_SCHEMA,
    },
    SERVICE_START_PROGRAM: {
        "method": "start_program",
        "schema": SERVICE_BASE_SCHEMA,
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve switch platform from a config entry."""

    bhyve = hass.data[DOMAIN][entry.entry_id][CONF_CLIENT]

    switches = []
    devices = filter_configured_devices(entry, await bhyve.devices)
    programs = await bhyve.timer_programs

    device_by_id = {}

    for device in devices:
        device_id = device.get("id")
        device_by_id[device_id] = device
        if device.get("type") == DEVICE_SPRINKLER:
            if not device.get("status"):
                _LOGGER.warning(
                    "Unable to configure device %s: the 'status' attribute is missing. Has it been paired with the wifi hub?",
                    device.get("name"),
                )
                continue

            # Filter out any programs which are not for this device
            device_programs = [
                program for program in programs if program.get("device_id") == device_id
            ]

            switches.append(
                BHyveRainDelaySwitch(hass, bhyve, device, "weather-pouring")
            )

            all_zones = device.get("zones")
            for zone in all_zones:
                zone_name = zone.get("name")
                # if the zone doesn't have a name, set it to the device's name if there is only one (eg a hose timer)
                if zone_name is None:
                    zone_name = (
                        device.get("name") if len(all_zones) == 1 else "Unnamed Zone"
                    )
                switches.append(
                    BHyveZoneSwitch(
                        hass,
                        bhyve,
                        device,
                        zone,
                        zone_name,
                        device_programs,
                        "water-pump",
                    )
                )

    for program in programs:
        program_device = device_by_id.get(program.get("device_id"))
        program_id = program.get("program")
        if program_device is not None and program_id is not None:
            _LOGGER.info("Creating switch: Program %s", program.get("name"))
            switches.append(
                BHyveProgramSwitch(
                    hass, bhyve, program_device, program, "bulletin-board"
                )
            )

    async_add_entities(switches, True)

    async def async_service_handler(service):
        """Map services to method of BHyve devices."""
        _LOGGER.info("%s service called", service.service)
        method = SERVICE_TO_METHOD.get(service.service)
        if not method:
            _LOGGER.warning("Unknown service method %s", service.service)
            return

        params = {
            key: value for key, value in service.data.items() if key != ATTR_ENTITY_ID
        }
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        component = hass.data.get(SWITCH_DOMAIN)
        if entity_ids:
            target_switches = [component.get_entity(entity) for entity in entity_ids]
        else:
            return

        method_name = method["method"]
        _LOGGER.debug("Service handler: %s %s", method_name, params)

        for entity in target_switches:
            if not hasattr(entity, method_name):
                _LOGGER.error("Service not implemented: %s", method_name)
                return
            await getattr(entity, method_name)(**params)

    for service, details in SERVICE_TO_METHOD.items():
        schema = details["schema"]
        hass.services.async_register(
            DOMAIN, service, async_service_handler, schema=schema
        )


class BHyveProgramSwitch(BHyveWebsocketEntity, SwitchEntity):
    """Define a BHyve program switch."""

    def __init__(self, hass, bhyve, device, program, icon):
        """Initialize the switch."""
        device_name = device.get("name", "Unknown switch")
        program_name = program.get("name", "unknown")

        name = f"{device_name} {program_name} program"

        super().__init__(hass, bhyve, device, name, icon, SwitchDeviceClass.SWITCH)

        self._program = program
        self._device_id = program.get("device_id")
        self._program_id = program.get("id")
        self._available = True

    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""

        attrs = {
            "device_id": self._device_id,
            "is_smart_program": self._program.get("is_smart_program", False),
            "frequency": self._program.get("frequency"),
            "start_times": self._program.get("start_times"),
            "budget": self._program.get("budget"),
            "program": self._program.get("program"),
            "run_times": self._program.get("run_times"),
        }

        return attrs

    @property
    def is_on(self):
        """Return the status of the sensor."""
        return self._program.get("enabled") is True

    @property
    def unique_id(self):
        """Return the unique id for the switch program."""
        return f"bhyve:program:{self._program_id}"

    @property
    def entity_category(self):
        """Zone program is a configuration category."""
        return EntityCategory.CONFIG

    async def _set_state(self, is_on):
        self._program.update({"enabled": is_on})
        await self._bhyve.update_program(self._program_id, self._program)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._set_state(False)

    async def start_program(self):
        """Begins running a program."""
        program_payload = self._program["program"]
        await self._send_program_message(program_payload)

    async def _send_program_message(self, station_payload):
        try:
            now = datetime.datetime.now()
            iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "event": EVENT_CHANGE_MODE,
                "mode": "manual",
                "device_id": self._device_id,
                "timestamp": iso_time,
                "program": station_payload,
            }
            _LOGGER.debug(payload)
            await self._bhyve.send_message(payload)

        except BHyveError as err:
            _LOGGER.warning("Failed to send to BHyve websocket message %s", err)
            raise (err)

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def update(device_id, data):
            """Update the state."""
            _LOGGER.info(
                "Program update: %s - %s - %s", self.name, self._program_id, str(data)
            )
            event = data.get("event")
            if event == EVENT_PROGRAM_CHANGED:
                self._ws_unprocessed_events.append(data)
                self.async_schedule_update_ha_state(True)

        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_PROGRAM.format(self._program_id), update
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()

    def _on_ws_data(self, data):
        #
        # {'event': 'program_changed' }
        #
        _LOGGER.info("Received program data update %s", data)

        event = data.get("event")
        if event is None:
            _LOGGER.warning("No event on ws data %s", data)
            return

        if event == EVENT_PROGRAM_CHANGED:
            program = data.get("program")
            if program is not None:
                self._program = program

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_PROGRAM_CHANGED]


class BHyveZoneSwitch(BHyveDeviceEntity, SwitchEntity):
    """Define a BHyve zone switch."""

    def __init__(self, hass, bhyve, device, zone, zone_name, device_programs, icon):
        """Initialize the switch."""
        self._is_on = False
        self._zone = zone
        self._zone_id = zone.get("station")
        self._entity_picture = zone.get("image_url")
        self._zone_name = zone_name
        self._smart_watering_enabled = zone.get("smart_watering_enabled")
        self._manual_preset_runtime = device.get(
            "manual_preset_runtime_sec", DEFAULT_MANUAL_RUNTIME.seconds
        )

        self._initial_programs = device_programs

        name = f"{self._zone_name} zone"
        _LOGGER.info("Creating switch: %s", name)

        super().__init__(hass, bhyve, device, name, icon, SwitchDeviceClass.SWITCH)

    def _setup(self, device):
        self._is_on = False
        self._attrs = {
            "device_name": self._device_name,
            "device_id": self._device_id,
            "zone_name": self._zone_name,
            "station": self._zone_id,
            ATTR_SMART_WATERING_ENABLED: self._smart_watering_enabled,
        }
        self._available = device.get("is_connected", False)

        status = device.get("status", {})
        watering_status = status.get("watering_status")

        _LOGGER.info("%s watering_status: %s", self.name, watering_status)

        zones = device.get("zones", [])

        zone = next(filter(lambda z: z.get("station") == self._zone_id, zones), None)

        if zone is not None:
            is_watering = (
                watering_status is not None
                and watering_status.get("current_station") == self._zone_id
            )
            self._is_on = is_watering
            self._attrs[ATTR_MANUAL_RUNTIME] = self._manual_preset_runtime

            next_start_time = orbit_time_to_local_time(
                status.get("next_start_time")
            )
            if next_start_time is not None:
                next_start_programs = status.get("next_start_programs")
                self._attrs.update(
                    {
                        ATTR_NEXT_START_TIME: next_start_time.isoformat(),
                        ATTR_NEXT_START_PROGRAMS: next_start_programs,
                    }
                )

            sprinkler_type = zone.get("sprinkler_type")
            if sprinkler_type is not None:
                self._attrs[ATTR_SPRINKLER_TYPE] = sprinkler_type

            image_url = zone.get("image_url")
            if image_url is not None:
                self._attrs[ATTR_IMAGE_URL] = image_url

            if is_watering:
                started_watering_at = watering_status.get("started_watering_station_at")
                current_station = watering_status.get("current_station")
                current_program = watering_status.get("program", None)
                stations = watering_status.get("stations")
                if stations:
                    current_runtime = stations[0].get("run_time")
                else:
                    current_runtime = None
                self._set_watering_started(
                    started_watering_at,
                    current_station,
                    current_program,
                    current_runtime,
                )

        if self._initial_programs is not None:
            programs = self._initial_programs
            for program in programs:
                self._set_watering_program(program)
            self._initial_programs = None

    def _set_watering_started(self, timestamp, station, program, runtime):
        started_watering_at_timestamp = (
            orbit_time_to_local_time(timestamp) if timestamp is not None else None
        )

        self._attrs.update(
            {
                ATTR_CURRENT_STATION: station,
                ATTR_CURRENT_PROGRAM: program,
                ATTR_CURRENT_RUNTIME: runtime,
                ATTR_STARTED_WATERING_AT: started_watering_at_timestamp,
            }
        )

    def _set_watering_program(self, program):
        if program is None:
            return

        program_name = program.get("name", "Unknown")
        program_id = program.get("program")
        program_enabled = program.get("enabled", False)

        if program_id is None:
            return

        program_attr = ATTR_PROGRAM.format(program_id)

        # Filter out any run times which are not for this switch
        active_program_run_times = list(
            filter(
                lambda x: (x.get("station") == self._zone_id),
                program.get("run_times", []),
            )
        )

        is_smart_program = program.get("is_smart_program", False)

        self._attrs[program_attr] = {
            "enabled": program_enabled,
            "name": program_name,
            "is_smart_program": is_smart_program,
        }

        if not program_enabled or not active_program_run_times:
            _LOGGER.info(
                "%s Zone: Watering program %s (%s) is not enabled, skipping",
                self._zone_name,
                program_name,
                program_id,
            )

            return

        #
        #    "name": "Backyard",
        #    "frequency": { "type": "days", "days": [1, 4] },
        #    "start_times": ["07:30"],
        #    "budget": 100,
        #    "program": "a",
        #    "run_times": [{ "run_time": 20, "station": 1 }],
        #

        if is_smart_program is True:
            upcoming_run_times = []
            for plan in program.get("watering_plan", []):
                run_times = plan.get("run_times")
                if run_times:
                    zone_times = list(
                        filter(lambda x: (x.get("station") == self._zone_id), run_times)
                    )
                    if zone_times:
                        plan_date = orbit_time_to_local_time(plan.get("date"))
                        for time in plan.get("start_times", []):
                            upcoming_time = dt.parse_time(time)
                            upcoming_run_times.append(
                                plan_date
                                + timedelta(
                                    hours=upcoming_time.hour,
                                    minutes=upcoming_time.minute,
                                )
                            )
            self._attrs[program_attr].update(
                {ATTR_SMART_WATERING_PLAN: upcoming_run_times}
            )
        else:
            self._attrs[program_attr].update(
                {
                    "start_times": program.get("start_times", []),
                    "frequency": program.get("frequency", []),
                    "run_times": active_program_run_times,
                }
            )

    def _should_handle_event(self, event_name, data):
        return event_name in [
            EVENT_CHANGE_MODE,
            EVENT_DEVICE_IDLE,
            EVENT_PROGRAM_CHANGED,
            EVENT_SET_MANUAL_PRESET_TIME,
            EVENT_WATERING_COMPLETE,
            EVENT_WATERING_IN_PROGRESS,
        ]

    def _on_ws_data(self, data):
        #
        # {'event': 'watering_in_progress_notification', 'program': 'e', 'current_station': 1, 'run_time': 14, 'started_watering_station_at': '2020-01-09T20:29:59.000Z', 'rain_sensor_hold': False, 'device_id': 'id', 'timestamp': '2020-01-09T20:29:59.000Z'}
        # {'event': 'device_idle', 'device_id': 'id', 'timestamp': '2020-01-10T12:32:06.000Z'}
        # {'event': 'set_manual_preset_runtime', 'device_id': 'id', 'seconds': 480, 'timestamp': '2020-01-18T17:00:35.000Z'}
        # {'event': 'program_changed' }
        #
        event = data.get("event")
        if event in (EVENT_DEVICE_IDLE, EVENT_WATERING_COMPLETE) or (
            event == EVENT_CHANGE_MODE and data.get("mode") in ("off", "auto")
        ):
            self._is_on = False
            self._set_watering_started(None, None, None, None)
        elif event == EVENT_WATERING_IN_PROGRESS:
            zone = data.get("current_station")
            if zone == self._zone_id:
                self._is_on = True
                started_watering_at = data.get("started_watering_station_at")
                current_station = data.get("current_station")
                current_program = data.get("program")
                current_runtime = data.get("run_time")

                self._set_watering_started(
                    started_watering_at,
                    current_station,
                    current_program,
                    current_runtime,
                )
        elif event == EVENT_SET_MANUAL_PRESET_TIME:
            self._manual_preset_runtime = data.get("seconds")
            self._attrs[ATTR_MANUAL_RUNTIME] = self._manual_preset_runtime
        elif event == EVENT_PROGRAM_CHANGED:
            watering_program = data.get("program")
            lifecycle_phase = data.get("lifecycle_phase")
            if lifecycle_phase != "destroy":
                self._set_watering_program(watering_program)
            else:
                self._attrs[ATTR_SMART_WATERING_PLAN] = None

    async def _send_station_message(self, station_payload):
        try:
            now = datetime.datetime.now()
            iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "event": EVENT_CHANGE_MODE,
                "mode": "manual",
                "device_id": self._device_id,
                "timestamp": iso_time,
                "stations": station_payload,
            }
            _LOGGER.info("Starting watering")
            await self._bhyve.send_message(payload)

        except BHyveError as err:
            _LOGGER.warning("Failed to send to BHyve websocket message %s", err)
            raise (err)

    @property
    def entity_picture(self):
        """Return picture of the entity."""
        return self._entity_picture

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this switch."""
        return f"{self._mac_address}:{self._device_id}:{self._zone_id}:switch"

    @property
    def is_on(self):
        """Return the status of the sensor."""
        return self._is_on

    async def set_smart_watering_soil_moisture(self, percentage):
        """Set the soil moisture percentage for the zone."""
        if self._smart_watering_enabled:
            landscape = None
            try:
                landscape = await self._bhyve.get_landscape(
                    self._device_id, self._zone_id
                )

            except BHyveError as err:
                _LOGGER.warning(
                    "Unable to retreive current soil data for %s: %s", self.name, err
                )

            if landscape is not None:
                _LOGGER.debug("Landscape data %s", landscape)

                # Define the minimum landscape update json payload
                landscape_update = {
                    "current_water_level": 0,
                    "device_id": "",
                    "id": "",
                    "station": 0,
                }

                # B-hyve computed value for 0% moisture
                landscape_moisture_level_0 = landscape["replenishment_point"]

                # B-hyve computed value for 100% moisture
                landscape_moisture_level_100 = landscape["field_capacity_depth"]

                # Set property to computed user desired soil moisture level
                landscape_update["current_water_level"] = landscape_moisture_level_0 + (
                    (
                        percentage
                        * (landscape_moisture_level_100 - landscape_moisture_level_0)
                    )
                    / 100.0
                )
                # Set remaining properties
                landscape_update["device_id"] = self._device_id
                landscape_update["id"] = landscape["id"]
                landscape_update["station"] = self._zone_id

                try:
                    _LOGGER.debug("Landscape update %s", landscape_update)
                    await self._bhyve.update_landscape(landscape_update)

                except BHyveError as err:
                    _LOGGER.warning(
                        "Unable to set soil moisture level for %s: %s", self.name, err
                    )
        else:
            _LOGGER.info(
                "Zone %s isn't smart watering enabled, cannot set soil moisture.",
                self._zone_name,
            )

    async def start_watering(self, minutes):
        """Turns on the switch and starts watering."""
        station_payload = [{"station": self._zone_id, "run_time": minutes}]
        self._is_on = True
        await self._send_station_message(station_payload)

    async def stop_watering(self):
        """Turns off the switch and stops watering."""
        station_payload = []
        self._is_on = False
        await self._send_station_message(station_payload)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        run_time = self._manual_preset_runtime / 60
        if run_time == 0:
            _LOGGER.warning(
                "Switch %s manual preset runtime is 0, watering has defaulted to %s minutes. Set the manual run time on your device or please specify number of minutes using the bhyve.start_watering service",
                self._device_name,
                int(DEFAULT_MANUAL_RUNTIME.seconds / 60),
            )
            run_time = 5

        await self.start_watering(run_time)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.stop_watering()


class BHyveRainDelaySwitch(BHyveDeviceEntity, SwitchEntity):
    """Define a BHyve rain delay switch."""

    def __init__(self, hass, bhyve, device, icon):
        """Initialize the switch."""
        name = "{} rain delay".format(device.get("name"))
        _LOGGER.info("Creating switch: %s", name)

        self._update_device_cb = None
        self._is_on = False

        super().__init__(hass, bhyve, device, name, icon, SwitchDeviceClass.SWITCH)

    def _setup(self, device):
        self._is_on = False
        self._attrs = {
            "device_id": self._device_id,
        }
        self._available = device.get("is_connected", False)

        device_status = device.get("status")
        rain_delay = device_status.get("rain_delay")

        self._update_device_cb = None
        self._extract_rain_delay(rain_delay, device_status)

    def _on_ws_data(self, data):
        #
        # {'event': 'rain_delay', 'device_id': 'id', 'delay': 0, 'timestamp': '2020-01-14T12:10:10.000Z'}
        #
        event = data.get("event")
        if event is None:
            _LOGGER.warning("No event on ws data %s", data)
            return

        if event == EVENT_RAIN_DELAY:
            self._extract_rain_delay(
                data.get("delay"), {"rain_delay_started_at": data.get("timestamp")}
            )
            # The REST API returns more data about a rain delay (eg cause/weather_type)
            self._update_device_soon()

    def _should_handle_event(self, event_name, data):
        return event_name in [EVENT_RAIN_DELAY]

    def _update_device_soon(self):
        if self._update_device_cb is not None:
            self._update_device_cb()  # unsubscribe
        self._update_device_cb = async_call_later(self._hass, 1, self._update_device)

    async def _update_device(self, time):
        await self._refetch_device(force_update=True)
        self.async_schedule_update_ha_state()

    def _extract_rain_delay(self, rain_delay, device_status=None):
        if rain_delay is not None and rain_delay > 0:
            self._is_on = True
            self._attrs = {ATTR_DELAY: rain_delay}
            if device_status is not None:
                self._attrs.update(
                    {
                        ATTR_CAUSE: device_status.get("rain_delay_cause"),
                        ATTR_WEATHER_TYPE: device_status.get("rain_delay_weather_type"),
                        ATTR_STARTED_AT: orbit_time_to_local_time(
                            device_status.get("rain_delay_started_at")
                        ),
                    }
                )
        else:
            self._is_on = False
            self._attrs = {}

    @property
    def is_on(self):
        """Return the status of the sensor."""
        return self._is_on

    @property
    def unique_id(self):
        """Return a unique, unchanging string that represents this sensor."""
        return f"{self._mac_address}:{self._device_id}:rain_delay"

    @property
    def entity_category(self):
        """Rain delay is a configuration category."""
        return EntityCategory.CONFIG

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        await self.enable_rain_delay()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        await self.disable_rain_delay()
