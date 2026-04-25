"""Support for Orbit BHyve valve (toggle zone)."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityDescription,
    ValveEntityFeature,
)
from homeassistant.components.valve.const import DOMAIN as VALVE_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt

from custom_components.bhyve.pybhyve.typings import BHyveZoneLandscape

from . import BHyveCoordinatorEntity
from .const import DEVICE_SPRINKLER, DOMAIN, EVENT_CHANGE_MODE
from .pybhyve.errors import BHyveError
from .util import orbit_time_to_local_time

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BHyveDataUpdateCoordinator
    from .pybhyve.typings import BHyveDevice, BHyveTimerProgram, BHyveZone

_LOGGER = logging.getLogger(__name__)

DEFAULT_MANUAL_RUNTIME = timedelta(minutes=5)

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


@dataclass(frozen=True, kw_only=True)
class BHyveValveEntityDescription(ValveEntityDescription):
    """Describes BHyve valve entity."""


VALVE_DESCRIPTION = BHyveValveEntityDescription(
    key="zone",
    translation_key="zone",
    device_class=ValveDeviceClass.WATER,
    reports_position=False,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve valve platform from a config entry."""
    coordinator: BHyveDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    devices: list[BHyveDevice] = hass.data[DOMAIN][entry.entry_id]["devices"]

    valves = []

    for device in devices:
        device_id = device.get("id")
        if device.get("type") == DEVICE_SPRINKLER:
            if not device.get("status"):
                _LOGGER.warning(
                    "Unable to configure device %s: the 'status' attribute is missing. "
                    "Has it been paired with the wifi hub?",
                    device.get("name"),
                )
                continue

            # Get programs for this device from coordinator
            device_programs = [
                program
                for program in coordinator.data.get("programs", {}).values()
                if program.get("device_id") == device_id
            ]

            all_zones = device.get("zones", [])
            for zone in all_zones:
                zone_name: str = zone.get("name") or (
                    device.get("name", "Unnamed Zone")
                    if len(all_zones) == 1
                    else "Unnamed Zone"
                )
                valves.append(
                    BHyveZoneValve(
                        coordinator,
                        device,
                        zone,
                        zone_name,
                        device_programs,
                    )
                )

    async_add_entities(valves)

    async def async_service_handler(service: Any) -> None:
        """Map services to method of BHyve devices."""
        _LOGGER.info("%s service called", service.service)
        method = SERVICE_TO_METHOD.get(service.service)
        if not method:
            _LOGGER.warning("Unknown service method %s", service.service)
            return

        params = {
            key: value for key, value in service.data.items() if key != ATTR_ENTITY_ID
        }
        entity_ids = service.data.get(ATTR_ENTITY_ID) or []
        method_name = method["method"]
        _LOGGER.debug("Service handler: %s %s", method_name, params)

        valve_component = hass.data.get(VALVE_DOMAIN)
        switch_component = hass.data.get(SWITCH_DOMAIN)

        for entity_id in entity_ids:
            entity = None
            if valve_component is not None:
                entity = valve_component.get_entity(entity_id)
            if entity is None and switch_component is not None:
                entity = switch_component.get_entity(entity_id)
            if entity is None:
                _LOGGER.error("Entity not found: %s", entity_id)
                continue
            if not hasattr(entity, method_name):
                _LOGGER.error(
                    "Service %s is not supported by entity %s",
                    method_name,
                    entity_id,
                )
                continue
            await getattr(entity, method_name)(**params)

    for service, details in SERVICE_TO_METHOD.items():
        schema = details["schema"]
        hass.services.async_register(
            DOMAIN, service, async_service_handler, schema=schema
        )


class BHyveZoneValve(BHyveCoordinatorEntity, ValveEntity):
    """Define a BHyve zone valve."""

    entity_description: BHyveValveEntityDescription
    _attr_has_entity_name = True
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        zone: BHyveZone,
        zone_name: str,
        device_programs: list[BHyveTimerProgram],
    ) -> None:
        """Initialize the valve."""
        self.entity_description = VALVE_DESCRIPTION
        if zone_name == device.get("name"):
            self._attr_name = "Zone"
        else:
            self._attr_name = f"{zone_name} zone"
        self._attr_translation_placeholders = {"zone_name": zone_name}

        super().__init__(coordinator, device)

        self._zone: BHyveZone = zone
        self._zone_id: str = zone.get("station", "")

        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{self._zone_id}:valve"
        )

        self._entity_picture: str | None = zone.get("image_url")
        self._zone_name: str = zone_name
        self._smart_watering_enabled: bool = zone.get("smart_watering_enabled", False)
        self._manual_preset_runtime: int = device.get(
            "manual_preset_runtime_sec", DEFAULT_MANUAL_RUNTIME.seconds
        )
        self._initial_programs = device_programs

    @property
    def is_closed(self) -> bool:
        """Return if valve is closed."""
        status = self.device_data.get("status", {})
        watering_status = status.get("watering_status")

        if watering_status:
            current_station = watering_status.get("current_station")
            # Valve is open (watering) if current_station matches this zone
            return str(current_station) != str(self._zone_id)
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attrs: dict[str, Any] = {
            "device_name": self._device_name,
            "device_id": self._device_id,
            "zone_name": self._zone_name,
            "station": self._zone_id,
            ATTR_SMART_WATERING_ENABLED: self._smart_watering_enabled,
            ATTR_MANUAL_RUNTIME: self._manual_preset_runtime,
        }

        status = self.device_data.get("status", {})
        watering_status = status.get("watering_status")

        # Get zone data from coordinator
        zones = self.device_data.get("zones", [])
        zone = next(filter(lambda z: z.get("station") == self._zone_id, zones), None)

        if zone is not None:
            # Add zone-specific attributes
            sprinkler_type = zone.get("sprinkler_type")
            if sprinkler_type is not None:
                attrs[ATTR_SPRINKLER_TYPE] = sprinkler_type

            image_url = zone.get("image_url")
            if image_url is not None:
                attrs[ATTR_IMAGE_URL] = image_url

        # Add next start time if available
        next_start_time = orbit_time_to_local_time(status.get("next_start_time"))
        if next_start_time is not None:
            next_start_programs = status.get("next_start_programs")
            attrs.update(
                {
                    ATTR_NEXT_START_TIME: next_start_time.isoformat(),
                    ATTR_NEXT_START_PROGRAMS: next_start_programs,
                }
            )

        # Add watering status if actively watering this zone
        if watering_status and str(watering_status.get("current_station")) == str(
            self._zone_id
        ):
            started_watering_at = watering_status.get("started_watering_station_at")
            started_watering_at_timestamp = (
                orbit_time_to_local_time(started_watering_at)
                if started_watering_at is not None
                else None
            )
            current_program = watering_status.get("program")
            stations = watering_status.get("stations")
            current_runtime = stations[0].get("run_time") if stations else None

            attrs.update(
                {
                    ATTR_CURRENT_STATION: watering_status.get("current_station"),
                    ATTR_CURRENT_PROGRAM: current_program,
                    ATTR_CURRENT_RUNTIME: current_runtime,
                    ATTR_STARTED_WATERING_AT: started_watering_at_timestamp,
                }
            )

        # Add program information
        for program in self.coordinator.data.get("programs", {}).values():
            if program.get("device_id") == self._device_id:
                self._add_program_attrs(attrs, program)

        # Get landscape data from coordinator
        landscapes = (
            self.coordinator.data.get("devices", {})
            .get(self._device_id, {})
            .get("landscapes", {})
        )
        landscape = landscapes.get(str(self._zone_id))
        if landscape:
            if landscape.get("image_url"):
                attrs["landscape_image"] = landscape["image_url"]
            if landscape.get("sprinkler_type"):
                attrs[ATTR_SPRINKLER_TYPE] = landscape["sprinkler_type"]

        return attrs

    def _add_program_attrs(
        self, attrs: dict[str, Any], program: BHyveTimerProgram
    ) -> None:
        """Add program attributes to the attrs dict."""
        program_name = program.get("name", "Unknown")
        program_id = program.get("program")
        program_enabled = program.get("enabled", False)

        if program_id is None:
            return

        # Filter out any run times which are not for this valve
        active_program_run_times = list(
            filter(
                lambda x: x.get("station") == self._zone_id,
                program.get("run_times", []),
            )
        )

        # Skip if program is disabled or has no run times for this zone
        if not program_enabled or not active_program_run_times:
            return

        is_smart_program = program.get("is_smart_program", False)
        program_attr = ATTR_PROGRAM.format(program_id)

        attrs[program_attr] = {
            "enabled": program_enabled,
            "name": program_name,
            "is_smart_program": is_smart_program,
        }

        if is_smart_program is True:
            upcoming_run_times = []
            for plan in program.get("watering_plan", []):
                run_times = plan.get("run_times")
                if run_times:
                    zone_times = list(
                        filter(lambda x: x.get("station") == self._zone_id, run_times)
                    )
                    if zone_times:
                        plan_date = orbit_time_to_local_time(plan.get("date"))
                        for time in plan.get("start_times", []):
                            upcoming_time = dt.parse_time(time)
                            if upcoming_time is not None and plan_date is not None:
                                upcoming_run_times.append(
                                    plan_date
                                    + timedelta(
                                        hours=upcoming_time.hour,
                                        minutes=upcoming_time.minute,
                                    )
                                )
            attrs[program_attr].update({ATTR_SMART_WATERING_PLAN: upcoming_run_times})
        else:
            attrs[program_attr].update(
                {
                    "start_times": program.get("start_times", []),
                    "frequency": program.get("frequency", []),
                    "run_times": active_program_run_times,
                }
            )

    @property
    def entity_picture(self) -> str | None:
        """Return picture of the entity."""
        return self._entity_picture

    async def _send_station_message(self, station_payload: Any) -> None:
        """Send a station control message via WebSocket."""
        try:
            now = datetime.datetime.now()  # noqa: DTZ005
            iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "event": EVENT_CHANGE_MODE,
                "mode": "manual",
                "device_id": self._device_id,
                "timestamp": iso_time,
                "stations": station_payload,
            }
            _LOGGER.debug("Sending message %s", payload)
            await self.coordinator.client.send_message(payload)
            # Coordinator updates via WebSocket event

        except BHyveError as err:
            _LOGGER.warning("Failed to send to BHyve websocket message %s", err)
            raise

    async def set_smart_watering_soil_moisture(self, percentage: float) -> None:
        """Set the soil moisture percentage for the zone."""
        if self._smart_watering_enabled:
            landscape = None
            try:
                landscape = await self.coordinator.client.get_landscape(
                    self._device_id, self._zone_id
                )

            except BHyveError as err:
                _LOGGER.warning(
                    "Unable to retreive current soil data for %s: %s", self.name, err
                )

            if landscape is not None:
                _LOGGER.debug("Landscape data %s", landscape)

                # Define the minimum landscape update json payload
                landscape_update = BHyveZoneLandscape(
                    {
                        "current_water_level": 0,
                        "device_id": "",
                        "id": "",
                        "station": 0,
                    }
                )

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
                    await self.coordinator.client.update_landscape(landscape_update)

                except BHyveError as err:
                    _LOGGER.warning(
                        "Unable to set soil moisture level for %s: %s", self.name, err
                    )
        else:
            _LOGGER.info(
                "Zone %s isn't smart watering enabled, cannot set soil moisture.",
                self._zone_name,
            )

    async def start_watering(self, minutes: float) -> None:
        """Open the valve and starts watering."""
        station_payload = [{"station": self._zone_id, "run_time": minutes}]
        self._attr_is_closed = False
        await self._send_station_message(station_payload)

    async def stop_watering(self) -> None:
        """Close the valve and stops watering."""
        station_payload = []
        self._attr_is_closed = True
        await self._send_station_message(station_payload)

    async def enable_rain_delay(self, hours: int = 24) -> None:
        """Enable rain delay for the device."""
        await self.coordinator.client.set_rain_delay(self._device_id, hours)

    async def disable_rain_delay(self) -> None:
        """Disable rain delay for the device."""
        await self.coordinator.client.set_rain_delay(self._device_id, 0)

    async def set_manual_preset_runtime(self, minutes: int) -> None:
        """Set the default watering runtime for the device."""
        await self.coordinator.client.set_manual_preset_runtime(
            self._device_id, minutes
        )

    async def async_open_valve(self) -> None:
        """Open the valve."""
        run_time = self._manual_preset_runtime / 60
        if run_time == 0:
            _LOGGER.warning(
                "Valve %s manual preset runtime is 0, watering has defaulted to %s minutes. Set the manual run time on your device or please specify number of minutes using the bhyve.start_watering service",  # noqa: E501
                self._device_name,
                int(DEFAULT_MANUAL_RUNTIME.seconds / 60),
            )
            run_time = 5

        await self.start_watering(run_time)

    async def async_close_valve(self) -> None:
        """Close the valve."""
        await self.stop_watering()
