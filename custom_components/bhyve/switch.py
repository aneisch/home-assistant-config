"""Support for Orbit BHyve switch (toggle zone)."""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from . import BHyveCoordinatorEntity
from .const import (
    DEVICE_SPRINKLER,
    DOMAIN,
    EVENT_CHANGE_MODE,
)
from .pybhyve.errors import BHyveError
from .pybhyve.typings import BHyveTimerProgram
from .util import orbit_time_to_local_time

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BHyveDataUpdateCoordinator
    from .pybhyve.typings import BHyveDevice

_LOGGER = logging.getLogger(__name__)

# Rain Delay Attributes
ATTR_CAUSE = "cause"
ATTR_DELAY = "delay"
ATTR_WEATHER_TYPE = "weather_type"
ATTR_STARTED_AT = "started_at"

# Keys accepted by the B-hyve API for program updates
PROGRAM_UPDATE_KEYS = {
    "budget",
    "device_id",
    "enabled",
    "frequency",
    "id",
    "name",
    "program",
    "program_start_date",
    "run_times",
    "start_times",
}

# Service constants
SERVICE_UPDATE_PROGRAM = "update_program"
ATTR_START_TIMES = "start_times"
ATTR_FREQUENCY = "frequency"
ATTR_BUDGET = "budget"

BUDGET_MIN = 0
BUDGET_MAX = 200

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_time_string(value: Any) -> str:
    """Validate an HH:MM time string."""
    if not isinstance(value, str) or not _TIME_RE.match(value):
        msg = f"Invalid time '{value}', expected HH:MM"
        raise vol.Invalid(msg)
    return value


FREQUENCY_SCHEMA = vol.Schema(
    {
        vol.Required("type"): cv.string,
        vol.Optional("days"): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Optional("interval"): vol.All(int, vol.Range(min=0)),
        vol.Optional("interval_hours"): vol.All(int, vol.Range(min=0)),
    },
    extra=vol.ALLOW_EXTRA,
)

UPDATE_PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
        vol.Optional(ATTR_START_TIMES): vol.All(
            cv.ensure_list, [_validate_time_string]
        ),
        vol.Optional(ATTR_FREQUENCY): FREQUENCY_SCHEMA,
        vol.Optional(ATTR_BUDGET): vol.All(
            vol.Coerce(int), vol.Range(min=BUDGET_MIN, max=BUDGET_MAX)
        ),
    }
)


@dataclass(frozen=True, kw_only=True)
class BHyveSwitchEntityDescription(SwitchEntityDescription):
    """Describes BHyve switch entity."""

    name: str = ""


def _create_program_switch(
    coordinator: BHyveDataUpdateCoordinator,
    device: BHyveDevice,
    program: BHyveTimerProgram,
) -> BHyveProgramSwitch:
    """Create a program switch entity."""
    return BHyveProgramSwitch(
        coordinator,
        device,
        program,
        BHyveSwitchEntityDescription(
            key="program",
            translation_key="program",
            icon="mdi:bulletin-board",
            entity_category=EntityCategory.CONFIG,
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve switch platform from a config entry."""
    coordinator: BHyveDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    devices: list[BHyveDevice] = hass.data[DOMAIN][entry.entry_id]["devices"]

    switches = []
    device_by_id = {}

    # Create rain delay switches for sprinkler devices
    for device in devices:
        device_id = device.get("id")
        device_by_id[device_id] = device
        if device.get("type") == DEVICE_SPRINKLER:
            if not device.get("status"):
                _LOGGER.warning(
                    "Unable to configure device %s: the 'status' attribute is missing. "
                    "Has it been paired with the wifi hub?",
                    device.get("name"),
                )
                continue

            switches.append(
                BHyveRainDelaySwitch(
                    coordinator,
                    device,
                    BHyveSwitchEntityDescription(
                        key="rain_delay",
                        translation_key="rain_delay",
                        name="Rain delay",
                        icon="mdi:weather-pouring",
                        entity_category=EntityCategory.CONFIG,
                    ),
                )
            )

            # Create smart watering switches for zones that support it
            smart_watering_desc = BHyveSwitchEntityDescription(
                key="smart_watering",
                translation_key="smart_watering",
                icon="mdi:auto-fix",
                entity_category=EntityCategory.CONFIG,
            )
            switches.extend(
                BHyveSmartWateringSwitch(coordinator, device, zone, smart_watering_desc)
                for zone in device.get("zones", [])
                if zone.get("smart_watering_enabled") is not None
            )

    # Create program switches (skip smart programs, handled above)
    for program in coordinator.data.get("programs", {}).values():
        if program.get("is_smart_program"):
            continue
        program_device = device_by_id.get(program.get("device_id"))
        if program_device is not None:
            _LOGGER.info("Creating switch: Program %s", program.get("name"))
            switches.append(
                _create_program_switch(coordinator, program_device, program)
            )

    async_add_entities(switches)

    async def async_update_program_service(call: ServiceCall) -> None:
        """Handle the update_program service call."""
        entity_ids = call.data.get(ATTR_ENTITY_ID) or []
        params = {k: v for k, v in call.data.items() if k != ATTR_ENTITY_ID}

        component = hass.data.get(SWITCH_DOMAIN)
        if component is None:
            _LOGGER.warning("Switch component not available, cannot update program")
            return

        for entity_id in entity_ids:
            entity = component.get_entity(entity_id)
            if not isinstance(entity, BHyveProgramSwitch):
                msg = f"Entity {entity_id} is not a BHyve program switch"
                raise ServiceValidationError(msg)
            await entity.async_update_program_config(**params)

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_PROGRAM):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_PROGRAM,
            async_update_program_service,
            schema=UPDATE_PROGRAM_SCHEMA,
        )

    # Listen for new programs created via WebSocket
    async def async_handle_program_created(event: Any) -> None:
        """Handle creation of new programs."""
        program = event.data.get("program")
        if not program or program.get("is_smart_program"):
            return

        program_device = device_by_id.get(program.get("device_id"))
        if program_device is None:
            _LOGGER.debug(
                "Program %s belongs to unknown device %s",
                program.get("id"),
                program.get("device_id"),
            )
            return

        _LOGGER.info("Creating switch for new program: %s", program.get("name"))
        async_add_entities(
            [_create_program_switch(coordinator, program_device, program)]
        )

    entry.async_on_unload(
        hass.bus.async_listen("bhyve_program_created", async_handle_program_created)
    )


class BHyveProgramSwitch(BHyveCoordinatorEntity, SwitchEntity):
    """Define a BHyve program switch."""

    entity_description: BHyveSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        program: BHyveTimerProgram,
        description: BHyveSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        self.entity_description = description
        program_name = program.get("name", "unknown")
        self._attr_name = f"{program_name} program"
        self._attr_translation_placeholders = {"program_name": program_name}

        super().__init__(coordinator, device)

        self._program_id = program.get("id", "0")
        self._attr_unique_id = f"bhyve:program:{self._program_id}"

    @property
    def program_data(self) -> dict[str, Any]:
        """Get program data from coordinator."""
        return self.coordinator.data.get("programs", {}).get(self._program_id, {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        program = self.program_data
        return {
            "device_id": self._device_id,
            "is_smart_program": program.get("is_smart_program", False),
            "frequency": program.get("frequency"),
            "start_times": program.get("start_times"),
            "budget": program.get("budget"),
            "program": program.get("program"),
            "run_times": program.get("run_times"),
        }

    @property
    def is_on(self) -> bool:
        """Return the status of the sensor."""
        return self.program_data.get("enabled") is True

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the switch on."""
        await self._update_program(enabled=True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the switch off."""
        await self._update_program(enabled=False)

    async def _update_program(self, *, enabled: bool) -> None:
        """Update a non-smart program via the API."""
        program = BHyveTimerProgram(
            {k: v for k, v in self.program_data.items() if k in PROGRAM_UPDATE_KEYS}
        )
        program["enabled"] = enabled
        await self.coordinator.client.update_program(self._program_id, program)

    async def async_update_program_config(
        self,
        start_times: list[str] | None = None,
        frequency: dict | None = None,
        budget: int | None = None,
    ) -> None:
        """Update configurable fields on a non-smart program."""
        if self.program_data.get("is_smart_program"):
            msg = "Cannot update configuration of a smart program"
            raise ServiceValidationError(msg)

        if start_times is None and frequency is None and budget is None:
            msg = "At least one of start_times, frequency or budget must be provided"
            raise ServiceValidationError(msg)

        program = BHyveTimerProgram(
            {k: v for k, v in self.program_data.items() if k in PROGRAM_UPDATE_KEYS}
        )
        changed: list[str] = []
        if start_times is not None:
            program["start_times"] = start_times
            changed.append("start_times")
        if frequency is not None:
            program["frequency"] = frequency
            changed.append("frequency")
        if budget is not None:
            program["budget"] = budget
            changed.append("budget")

        _LOGGER.info(
            "Updating program %s, changed fields: %s", self._program_id, changed
        )
        await self.coordinator.client.update_program(self._program_id, program)

    async def start_program(self) -> None:
        """Begins running a program."""
        program_payload = self.program_data.get("program")
        if program_payload:
            await self._send_program_message(program_payload)

    async def _send_program_message(self, station_payload: Any) -> None:
        try:
            now = datetime.datetime.now()  # noqa: DTZ005
            iso_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = {
                "event": EVENT_CHANGE_MODE,
                "mode": "manual",
                "device_id": self._device_id,
                "timestamp": iso_time,
                "program": station_payload,
            }
            _LOGGER.debug(payload)
            await self.coordinator.client.send_message(payload)

        except BHyveError as err:
            _LOGGER.warning("Failed to send to BHyve websocket message %s", err)
            raise


class BHyveSmartWateringSwitch(BHyveCoordinatorEntity, SwitchEntity):
    """Define a BHyve smart watering switch for a zone."""

    entity_description: BHyveSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        zone: dict,
        description: BHyveSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        self.entity_description = description
        self._zone_id = zone.get("station")
        zone_name = zone.get("name", "")
        all_zones = device.get("zones", [])
        if zone_name and zone_name != device.get("name") and len(all_zones) > 1:
            self._attr_name = f"{zone_name} smart watering"
        else:
            self._attr_name = "Smart watering"
        self._attr_translation_placeholders = {"zone_name": zone_name}

        super().__init__(coordinator, device)

        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{self._zone_id}:smart_watering"
        )

    def _get_zone_data(self) -> dict:
        """Get current zone data from coordinator."""
        for zone in self.device_data.get("zones", []):
            if zone.get("station") == self._zone_id:
                return zone
        return {}

    @property
    def is_on(self) -> bool:
        """Return true if smart watering is enabled for this zone."""
        return self._get_zone_data().get("smart_watering_enabled", False)

    async def _set_smart_watering(self, *, enabled: bool) -> None:
        """Update the zone's smart_watering_enabled on the device."""
        zones = [
            {**z, "smart_watering_enabled": enabled}
            if z.get("station") == self._zone_id
            else z
            for z in self.device_data.get("zones", [])
        ]
        await self.coordinator.client.update_device(
            {"id": self._device_id, "zones": zones}
        )

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn smart watering on."""
        await self._set_smart_watering(enabled=True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn smart watering off."""
        await self._set_smart_watering(enabled=False)


class BHyveRainDelaySwitch(BHyveCoordinatorEntity, SwitchEntity):
    """Define a BHyve rain delay switch."""

    entity_description: BHyveSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        description: BHyveSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        self.entity_description = description
        self._attr_name = description.name

        super().__init__(coordinator, device)

        self._attr_unique_id = f"{self._mac_address}:{self._device_id}:rain_delay"

    @property
    def is_on(self) -> bool:
        """Return the status of the sensor."""
        status = self.device_data.get("status", {})
        rain_delay = status.get("rain_delay", 0)
        return rain_delay is not None and rain_delay > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        status = self.device_data.get("status", {})
        rain_delay = status.get("rain_delay", 0)

        if rain_delay is not None and rain_delay > 0:
            attrs: dict[str, Any] = {ATTR_DELAY: rain_delay}
            attrs.update(
                {
                    ATTR_CAUSE: status.get("rain_delay_cause", "Unknown"),
                    ATTR_WEATHER_TYPE: status.get("rain_delay_weather_type", "Unknown"),
                    ATTR_STARTED_AT: orbit_time_to_local_time(
                        status.get("rain_delay_started_at", "")
                    ),
                }
            )
            return attrs
        return {}

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the switch on."""
        await self.enable_rain_delay()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the switch off."""
        await self.disable_rain_delay()

    async def enable_rain_delay(self, hours: int = 24) -> None:
        """Enable rain delay for the device."""
        await self.coordinator.client.set_rain_delay(self._device_id, hours)

    async def disable_rain_delay(self) -> None:
        """Disable rain delay for the device."""
        await self.coordinator.client.set_rain_delay(self._device_id, 0)
