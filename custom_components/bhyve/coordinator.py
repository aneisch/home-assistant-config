"""DataUpdateCoordinator for B-hyve integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEVICE_SPRINKLER,
    DOMAIN,
    EVENT_BATTERY_STATUS,
    EVENT_CHANGE_MODE,
    EVENT_DEVICE_IDLE,
    EVENT_FAULT,
    EVENT_FS_ALARM,
    EVENT_RAIN_DELAY,
    EVENT_SET_MANUAL_PRESET_TIME,
    EVENT_WATERING_COMPLETE,
    EVENT_WATERING_IN_PROGRESS,
)
from .pybhyve.errors import AuthenticationError, BHyveError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .pybhyve import BHyveClient
    from .pybhyve.typings import BHyveDevice

_LOGGER = logging.getLogger(__name__)


class BHyveDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching B-hyve data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BHyveClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),  # Poll every 5 minutes
        )
        self.client = client
        self.entry = entry
        self.gateway_to_bridge: dict[str, str] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API (periodic polling)."""
        try:
            # devices and timer_programs are independent endpoints; fetch in
            # parallel so the refresh is bounded by the slower of the two.
            devices, programs = await asyncio.gather(
                self.client.devices,
                self.client.timer_programs,
            )

            # Fan out per-device history/landscape fetches across all devices in
            # parallel. Previously this loop was sequential across devices, so
            # multi-device accounts paid N times the per-device roundtrip.
            device_results = await asyncio.gather(
                *[self._fetch_device_bundle(device) for device in devices],
                return_exceptions=True,
            )

            data: dict[str, Any] = {
                "devices": {},
                "programs": {},
            }

            for result in device_results:
                if isinstance(result, BaseException):
                    _LOGGER.debug("Error fetching device bundle: %s", result)
                    continue
                if result is None:
                    continue
                data["devices"][result["device"]["id"]] = result

            for program in programs:
                program_id = program.get("id")
                if program_id:
                    data["programs"][program_id] = program

            return data  # noqa: TRY300

        except AuthenticationError as err:
            _LOGGER.warning("Authentication failed, triggering reauth: %s", err)
            raise ConfigEntryAuthFailed from err
        except (BHyveError, TimeoutError) as err:
            msg = f"Error communicating with API: {err}"
            raise UpdateFailed(msg) from err

    async def _fetch_device_bundle(self, device: BHyveDevice) -> dict[str, Any] | None:
        """Fetch history + landscapes for a single device."""
        device_id = device.get("id")
        if not device_id:
            return None

        if device.get("type") == DEVICE_SPRINKLER:
            history, landscapes = await asyncio.gather(
                self._fetch_device_history(device_id),
                self._fetch_landscapes(device_id, device),
                return_exceptions=True,
            )

            if isinstance(history, Exception):
                _LOGGER.debug(
                    "Error fetching history for device %s: %s", device_id, history
                )
                history = []
            if isinstance(landscapes, Exception):
                _LOGGER.debug(
                    "Error fetching landscapes for device %s: %s",
                    device_id,
                    landscapes,
                )
                landscapes = {}
        else:
            history = []
            landscapes = {}

        return {
            "device": device,
            "history": history,
            "landscapes": landscapes,
        }

    async def _fetch_device_history(self, device_id: str) -> list[dict[str, Any]]:
        """Fetch watering history for a device."""
        try:
            history = await self.client.get_device_history(device_id)
        except (BHyveError, TimeoutError) as err:
            _LOGGER.debug("Could not fetch history for device %s: %s", device_id, err)
            return []
        else:
            return history if isinstance(history, list) else []

    async def _fetch_landscapes(
        self, device_id: str, device: BHyveDevice
    ) -> dict[str, dict[str, Any]]:
        """Fetch landscape information for all zones on a device in parallel."""
        landscapes: dict[str, dict[str, Any]] = {}
        zones = device.get("zones", [])

        if not zones:
            return landscapes

        # Fetch all zone landscapes in parallel
        async def fetch_zone_landscape(
            zone: dict[str, Any],
        ) -> tuple[str | None, dict | None]:
            """Fetch landscape for a single zone."""
            zone_id = zone.get("station")
            if not zone_id:
                return None, None

            try:
                landscape = await self.client.get_landscape(device_id, zone_id)
                return str(zone_id), landscape or None
            except (BHyveError, TimeoutError) as err:
                _LOGGER.debug(
                    "Could not fetch landscape for device %s zone %s: %s",
                    device_id,
                    zone_id,
                    err,
                )
                return str(zone_id), None

        # Gather all landscape fetches in parallel
        results = await asyncio.gather(
            *[fetch_zone_landscape(zone) for zone in zones],
            return_exceptions=True,
        )

        # Process results
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.debug(
                    "Exception fetching landscape for device %s: %s",
                    device_id,
                    result,
                )
                continue

            # Type checker doesn't know result is tuple after Exception filter
            if isinstance(result, tuple):
                zone_id, landscape = result
                if zone_id and landscape:
                    landscapes[zone_id] = landscape

        return landscapes

    @staticmethod
    def _apply_watering_in_progress(
        device_data: dict[str, Any], event_data: dict[str, Any]
    ) -> None:
        """Apply a watering_in_progress_notification event to device state."""
        status = device_data.setdefault("status", {})
        current_station = event_data.get("current_station")
        run_time = event_data.get("run_time")
        stations = event_data.get("stations") or []
        # The event provides run_time at the top level without a stations array.
        # Synthesize one so the shape matches the API response and
        # current_runtime stays populated for valve entities.
        if not stations and run_time is not None and current_station is not None:
            stations = [{"station": current_station, "run_time": run_time}]
        status["watering_status"] = {
            "current_station": current_station,
            "program": event_data.get("program"),
            "run_time": run_time,
            "started_watering_station_at": event_data.get(
                "started_watering_station_at"
            ),
            "stations": stations,
        }
        status["run_mode"] = event_data.get("mode", "manual")

    async def async_handle_device_event(self, event_data: dict[str, Any]) -> None:  # noqa: PLR0912
        """Handle WebSocket device events."""
        if not self.data:
            _LOGGER.debug("Coordinator data not initialized, ignoring event")
            return

        device_id = event_data.get("device_id")
        event = event_data.get("event")

        if not device_id or device_id not in self.data["devices"]:
            _LOGGER.debug(
                "Device %s not found in coordinator data, ignoring event %s",
                device_id,
                event,
            )
            return

        # Update specific device data based on event type
        device_data = self.data["devices"][device_id]["device"]

        if event == EVENT_BATTERY_STATUS:
            # Update battery information
            if "battery" in event_data:
                device_data["battery"] = event_data["battery"]

        elif event == EVENT_CHANGE_MODE:
            # Update device status with mode change data
            if "status" not in device_data:
                device_data["status"] = {}
            device_data["status"].update(event_data)

        elif event == EVENT_DEVICE_IDLE:
            # Device went idle, update status
            if "status" not in device_data:
                device_data["status"] = {}
            device_data["status"]["run_mode"] = "off"
            if "watering_status" in device_data["status"]:
                del device_data["status"]["watering_status"]

        elif event == EVENT_WATERING_IN_PROGRESS:
            self._apply_watering_in_progress(device_data, event_data)

        elif event == EVENT_WATERING_COMPLETE:
            # Clear watering status
            if "status" not in device_data:
                device_data["status"] = {}
            if "watering_status" in device_data["status"]:
                del device_data["status"]["watering_status"]
            device_data["status"]["run_mode"] = "off"

        elif event == EVENT_RAIN_DELAY:
            # Update rain delay info
            if "status" not in device_data:
                device_data["status"] = {}
            device_data["status"]["rain_delay"] = event_data.get("delay", 0)

        elif event == EVENT_FAULT:
            # Update station fault information
            if "status" not in device_data:
                device_data["status"] = {}
            device_data["status"]["station_faults"] = event_data.get(
                "station_faults", []
            )

        elif event == EVENT_FS_ALARM:
            # Update flood sensor status with only meaningful flood sensor fields.
            # Avoid a blind merge that could overwrite unrelated device-level keys.
            if "status" not in device_data:
                device_data["status"] = {}
            for key in (
                "flood_alarm_status",
                "temp_alarm_status",
                "temp_f",
                "rssi",
                "last_flood_alarm_at",
                "last_temp_alarm_at",
                "status_updated_at",
            ):
                if key in event_data:
                    device_data["status"][key] = event_data[key]

        elif event == EVENT_SET_MANUAL_PRESET_TIME:
            # Update manual preset runtime
            if "status" not in device_data:
                device_data["status"] = {}
            device_data["status"]["manual_preset_runtime"] = event_data.get("runtime")

        # Notify all listening entities
        self.async_set_updated_data(self.data)

    def _set_zones_smart_watering(
        self, device_id: str | None, *, enabled: bool
    ) -> None:
        """Update smart_watering_enabled on all zones of a device."""
        if not device_id:
            return
        device_data = self.data.get("devices", {}).get(device_id, {})
        device = device_data.get("device", {})
        for zone in device.get("zones", []):
            zone["smart_watering_enabled"] = enabled

    @staticmethod
    def _get_program_id(event_data: dict[str, Any]) -> str | None:
        """Extract program ID from event data."""
        program_id = event_data.get("program_id")
        if not program_id:
            program = event_data.get("program", {})
            program_id = program.get("id") if isinstance(program, dict) else None
        return program_id

    async def async_handle_program_event(self, event_data: dict[str, Any]) -> None:
        """Handle WebSocket program events."""
        if not self.data:
            _LOGGER.debug("Coordinator data not initialized, ignoring event")
            return

        lifecycle_phase = event_data.get("lifecycle_phase")
        program_id = self._get_program_id(event_data)

        if not program_id:
            _LOGGER.debug("No program_id found in event, ignoring")
            return

        # Handle program creation
        if lifecycle_phase == "create":
            program_data = event_data.get("program")
            if isinstance(program_data, dict):
                _LOGGER.debug("Adding new program %s to coordinator data", program_id)
                self.data["programs"][program_id] = program_data
                if program_data.get("is_smart_program"):
                    # Smart program created means smart watering was enabled
                    device_id = event_data.get("device_id")
                    self._set_zones_smart_watering(device_id, enabled=True)
                else:
                    self.hass.bus.async_fire(
                        "bhyve_program_created",
                        {"program_id": program_id, "program": program_data},
                    )
            self.async_set_updated_data(self.data)
            return

        # Handle program deletion (smart programs use "destroy" but should
        # be kept as entities since they represent a toggle, not a removal)
        if lifecycle_phase in ("delete", "destroy"):
            is_smart = (
                self.data["programs"].get(program_id, {}).get("is_smart_program", False)
            )
            if not is_smart and program_id in self.data["programs"]:
                _LOGGER.debug("Removing program %s from coordinator data", program_id)
                del self.data["programs"][program_id]
                self.hass.bus.async_fire(
                    "bhyve_program_deleted",
                    {"program_id": program_id},
                )
                self.async_set_updated_data(self.data)
                return
            if is_smart:
                # Smart program destroy means smart watering was disabled.
                # Update zone data so smart watering switches reflect the change.
                device_id = event_data.get("device_id")
                self._set_zones_smart_watering(device_id, enabled=False)
                # Fall through to update the program data

        # For update events, check if program exists
        if program_id not in self.data["programs"]:
            _LOGGER.debug(
                "Program %s not found in coordinator data, ignoring event",
                program_id,
            )
            return

        # Update program data
        program_data = event_data.get("program")
        if isinstance(program_data, dict):
            self.data["programs"][program_id].update(program_data)
        # If no program data provided, just update enabled status
        elif "enabled" in event_data:
            self.data["programs"][program_id]["enabled"] = event_data["enabled"]

        # Notify all listening entities
        self.async_set_updated_data(self.data)
