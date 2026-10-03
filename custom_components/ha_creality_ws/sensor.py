"""Sensor entities for Creality 3D printers."""
from __future__ import annotations
import logging
import json
import math
from collections.abc import Callable, Mapping
from typing import Any
from .utils import (
    build_spool_key as _build_spool_key,
    derive_print_state as _derive_print_state,
    format_filament_label as _format_filament_label,
    normalize_color_hex as _normalize_color_hex,
    parse_position as _parse_position,
    safe_float as _safe_float,
)

from homeassistant.core import callback  # type: ignore[import]
from homeassistant.components.sensor import (  # type: ignore[import]
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (  # type: ignore[import]
    PERCENTAGE as U_PERCENT,
    EntityCategory,
    UnitOfLength,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect # type: ignore[import]
from .entity import KEntity
from .const import DOMAIN, GCODE_INFO_KEY


_LOGGER = logging.getLogger(__name__)



U_C = UnitOfTemperature.CELSIUS
U_MM = UnitOfLength.MILLIMETERS
U_CM = UnitOfLength.CENTIMETERS
U_S = UnitOfTime.SECONDS
U_G = UnitOfMass.GRAMS


# ----------------- helpers -----------------

def _attr_dict(*pairs: tuple[str, Any]) -> dict[str, Any]:
    return {k: v for (k, v) in pairs if v is not None}


def _gcode_info(coordinator) -> Mapping[str, Any] | None:
    """The slicer's metadata for the running job, if the printer supplied any.

    The coordinator reduces the printer's whole-listing reply to this one entry
    and clears it when the running file changes, so anything here describes the
    current job or is absent.
    """
    info = (coordinator.data or {}).get(GCODE_INFO_KEY)
    return info if isinstance(info, Mapping) else None


def _expected_length_mm(coordinator) -> float | None:
    """Slicer-estimated filament length for the running job, in mm.

    `consumables` shares its unit with the `usedMaterialLength` the printer
    streams, which is what makes the two directly comparable. A zero is treated
    as no answer rather than a real estimate -- no job consumes nothing, and it
    is the denominator of the consumption percentage.
    """
    info = _gcode_info(coordinator)
    if info is None:
        return None
    mm = _safe_float(info.get("consumables"))
    # `mm and mm > 0` rejects NaN but not inf, and `json.loads` accepts an
    # `Infinity` token, so a non-finite length would reach the state
    # machine and be recorded in statistics.
    return mm if mm is not None and math.isfinite(mm) and mm > 0 else None

# position parsing moved to utils.parse_position


# ----------------- dynamic “simple field” sensors -----------------

# Use special fields for computed/fallback values:
#   "__pos_x__", "__pos_y__", "__pos_z__" from curPosition
#   "__progress__" -> printProgress or dProgress
SPECS: list[dict[str, Any]] = [
    # Temperatures
    {
        "uid": "bed_temperature",
        "name": "Bed Temperature",
        "translation_key": "bed_temperature",
        "field": "bedTemp0",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": U_C,
        "attrs": lambda d: _attr_dict(
            ("target", d.get("targetBedTemp0")),
            ("max", d.get("maxBedTemp")),
        ),
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "box_temperature",  # keep uid stable for existing entity IDs
        "name": "Chamber Temperature",
        "translation_key": "chamber_temperature",
        "field": "boxTemp",  # protocol field remains boxTemp
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": U_C,
        "attrs": lambda d: _attr_dict(
            ("target", d.get("targetBoxTemp")),
            ("max", d.get("maxBoxTemp")),
        ),
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "nozzle_temperature",
        "name": "Nozzle Temperature",
        "translation_key": "nozzle_temperature",
        "field": "nozzleTemp",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": U_C,
        "attrs": lambda d: _attr_dict(
            ("target", d.get("targetNozzleTemp")),
            ("max", d.get("maxNozzleTemp")),
        ),
        "state_class": SensorStateClass.MEASUREMENT,
    },

    # Print progress (with fallback)
    {
        "uid": "print_progress",
        "name": "Print Progress",
        "translation_key": "print_progress",
        "field": "__progress__",
        "device_class": None,
        "unit": U_PERCENT,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },

    # Layers
    {
        "uid": "total_layers",
        "name": "Total Layers",
        "translation_key": "total_layers",
        "field": "TotalLayer",
        "device_class": None,
        "unit": None,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "current_layer",
        "name": "Working Layer",
        "translation_key": "current_layer",
        "field": "layer",
        "device_class": None,
        "unit": None,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },

    # Positions (computed from curPosition)
    {
        "uid": "position_x",
        "name": "Position X",
        "translation_key": "position_x",
        "field": "__pos_x__",
        "device_class": SensorDeviceClass.DISTANCE,
        "unit": U_MM,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "position_y",
        "name": "Position Y",
        "translation_key": "position_y",
        "field": "__pos_y__",
        "device_class": SensorDeviceClass.DISTANCE,
        "unit": U_MM,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "position_z",
        "name": "Position Z",
        "translation_key": "position_z",
        "field": "__pos_z__",
        "device_class": SensorDeviceClass.DISTANCE,
        "unit": U_MM,
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },

    # Speed/flow (current)
    {
        "uid": "feedrate_pct",
        "name": "Print Speed %",
        "translation_key": "feedrate_pct",
        "field": "curFeedratePct",
        "device_class": None,
        "unit": "%",
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "uid": "flowrate_pct",
        "name": "Flow Rate %",
        "translation_key": "flowrate_pct",
        "field": "curFlowratePct",
        "device_class": None,
        "unit": "%",
        "attrs": lambda d: {},
        "state_class": SensorStateClass.MEASUREMENT,
    },
]

# ----------------- dynamic "mapped" sensors -----------------
MAPPED_SPECS: list[dict[str, Any]] = [
    {
        "uid": "filament_status",
        "name": "Filament Status",
        "translation_key": "filament_status",
        "field": "materialStatus",
        "mapping": {
            0: "normal",
            1: "runout",
        },
        "icon": "mdi:printer-3d-nozzle-alert",
    },
]


class KSimpleFieldSensor(KEntity, SensorEntity):
    """Generic sensor bound to one telemetry field or a special computed field."""

    def __init__(self, coordinator, spec: dict[str, Any]):
        super().__init__(coordinator, spec["name"], spec["uid"], translation_key=spec.get("translation_key"))
        self._field: str = spec["field"]
        self._attr_device_class = spec.get("device_class")
        self._attr_native_unit_of_measurement = spec.get("unit")
        self._attr_state_class = spec.get("state_class")
        self._get_attrs: Callable[[dict[str, Any]], dict[str, Any]] = spec.get("attrs") or (lambda d: {})

    @property
    def available(self) -> bool:
        # System entity (model) is always available if we have cached info
        if self._field == "model":
            return True
        return super().available

    def _zero_value(self):
        """Return appropriate zero value for offline/off state."""
        if self._field in ("TotalLayer", "layer"):
            return 0
        if self._attr_native_unit_of_measurement is None and self._field not in ("__pos_x__", "__pos_y__", "__pos_z__", "__progress__"):
            return None
        return 0

    @property
    def native_value(self):
        # System entity (model) uses cached data from config entry, never live data
        if self._field == "model":
            cached_info = self._get_cached_device_info()
            if cached_info and cached_info.get("model"):
                return cached_info.get("model")
            # Fallback to current data if no cached model
            d = self.coordinator.data
            return d.get(self._field) if d else None
        
        d = self.coordinator.data
        
        # System entity should not be zeroed when printer is off - it shows cached info
        if self._should_zero() and self._field != "model":
            return self._zero_value()

        # Position parsing (computed from curPosition string)
        if self._field in ("__pos_x__", "__pos_y__", "__pos_z__"):
            x, y, z = _parse_position(d)
            return {"__pos_x__": x, "__pos_y__": y, "__pos_z__": z}[self._field]

        # Print progress
        if self._field == "__progress__":
            return d.get("printProgress") or d.get("dProgress")

        return d.get(self._field)

    @property
    def extra_state_attributes(self):
        # System entity (model) uses cached data from config entry, never live data
        if self._field == "model":
            cached_info = self._get_cached_device_info()
            if cached_info:
                d = {}
                if cached_info.get("hostname"):
                    d["hostname"] = cached_info.get("hostname")
                if cached_info.get("modelVersion"):
                    d["modelVersion"] = cached_info.get("modelVersion")
                return d
        
        return self._get_attrs(self.coordinator.data)


class KMappedSensor(KEntity, SensorEntity):
    """Sensor that maps integer values to human-readable strings."""
    
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, spec: dict[str, Any]):
        super().__init__(coordinator, spec["name"], spec["uid"], translation_key=spec.get("translation_key"))
        self._field: str = spec["field"]
        self._mapping: dict[int, str] = spec.get("mapping", {})
        if spec.get("icon"):
            self._attr_icon = spec["icon"]

    @property
    def native_value(self) -> str | None:
        if self._should_zero():
            return "unknown"

        d = self.coordinator.data
        if not d:
            return "unknown"

        raw = d.get(self._field)
        if raw is None:
            return "unknown"

        try:
            val = int(raw)
            return self._mapping.get(val, str(raw))
        except (ValueError, TypeError):
            return str(raw)


class PrintStatusSensor(KEntity, SensorEntity):
    _attr_translation_key = "print_status"
    _attr_icon = "mdi:printer-3d"

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="print_status")

    @property
    def native_value(self) -> str | None:
        # The mapping lives in utils.derive_print_state so that services gating on
        # "is the printer busy" use the same definition the dashboard shows.
        return _derive_print_state(
            self.coordinator.data or {},
            power_off=self.coordinator.power_is_off(),
            available=self.coordinator.available,
            paused_flag=self.coordinator.paused_flag(),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data or {}
        attrs = {
            "file": d.get("printFileName") or "",
            "progress": d.get("printProgress") or d.get("dProgress"),
            "job_time_s": d.get("printJobTime"),
            "left_time_s": d.get("printLeftTime"),
            "used_material_mm": d.get("usedMaterialLength"),
            "real_time_flow_mm3_s": _safe_float(d.get("realTimeFlow")),
            "paused_flag": self.coordinator.paused_flag(),
            "state_raw": d.get("state"),
            "err": d.get("err"),
        }
        # Most firmware reports `err` as a mapping, some as a bare code, and
        # `derive_print_state` has handled both since the state it derives
        # depends on it. Here it was still `.get()`-ed unconditionally, so a
        # bare code raised AttributeError while the attribute dict was being
        # built -- taking every attribute down, not just this one. `err` is
        # published raw above either way.
        err_raw = d.get("err")
        err_code = err_raw.get("errcode", 0) if isinstance(err_raw, Mapping) else err_raw
        err_value = _safe_float(err_code)
        if err_value is not None and err_value != 0:
            attrs["error_code"] = err_code
            # The error message mapping function is not yet implemented, so it remains commented out.
            # attrs["error_message"] = self._map_error_code_to_message(err_code)
        
        return attrs


class UsedMaterialLengthSensor(KEntity, SensorEntity):
    _attr_translation_key = "used_material_length"
    _attr_icon = "mdi:counter"
    _attr_native_unit_of_measurement = U_CM
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="used_material_length")

    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return 0.0
        v = self.coordinator.data.get("usedMaterialLength")
        try:
            mm = float(v)
            return round(mm / 10.0, 2)
        except (TypeError, ValueError):
            return None

class ExpectedMaterialLengthSensor(KEntity, SensorEntity):
    _attr_translation_key = "expected_material_length"
    _attr_icon = "mdi:ruler"
    _attr_native_unit_of_measurement = U_CM
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="expected_material_length")

    @property
    def native_value(self) -> float | None:
        # Not zeroed when the printer is off or unreachable, unlike the live
        # measurements: this describes a file, and a stale estimate stays true
        # in a way a stale temperature does not.
        mm = _expected_length_mm(self.coordinator)
        # In cm to match UsedMaterialLengthSensor, so the two can be compared
        # or subtracted without converting one of them first.
        return None if mm is None else round(mm / 10.0, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = _gcode_info(self.coordinator) or {}
        # Passed through as the printer words them. On a multi-material job
        # these fields carry several values in one string, and this integration
        # has no hardware to confirm how they are delimited -- so they are
        # published raw rather than split into something possibly wrong.
        return _attr_dict(
            ("material", info.get("material") or None),
            ("color", info.get("materialColors") or None),
            ("slicer", info.get("software") or None),
            ("estimated_time_s", _safe_float(info.get("timeCost"))),
            ("gcode_file", info.get("name") or None),
        )


class ExpectedMaterialWeightSensor(KEntity, SensorEntity):
    _attr_translation_key = "expected_material_weight"
    _attr_icon = "mdi:weight-gram"
    _attr_native_unit_of_measurement = U_G
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="expected_material_weight")

    @property
    def native_value(self) -> float | None:
        info = _gcode_info(self.coordinator)
        if info is None:
            return None
        # Empty on files the printer did not slice itself -- Creality Print
        # output and the stock sample models both arrive with a blank weight
        # and a usable length. Multi-material jobs put several weights in this
        # one string, which `_safe_float` also declines. Either way the sensor
        # goes unknown, which beats publishing one filament's weight as the
        # whole job's.
        grams = _safe_float(info.get("filamentWeight"))
        # NaN compares false against everything, so `<= 0` lets it past.
        if grams is None or not math.isfinite(grams) or grams <= 0:
            return None
        return round(grams, 2)


class FilamentConsumptionSensor(KEntity, SensorEntity):
    _attr_translation_key = "filament_consumption"
    _attr_icon = "mdi:printer-3d-nozzle"
    _attr_native_unit_of_measurement = U_PERCENT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="filament_consumption")

    @property
    def native_value(self) -> float | None:
        expected_mm = _expected_length_mm(self.coordinator)
        if expected_mm is None:
            return None
        used_mm = _safe_float((self.coordinator.data or {}).get("usedMaterialLength"))
        if used_mm is None or not math.isfinite(used_mm):
            return None
        # Left uncapped on purpose. A job that runs past its estimate has
        # genuinely used more filament than the slicer predicted, and clamping
        # to 100% would hide exactly the case worth seeing.
        return round(used_mm / expected_mm * 100.0, 1)


class PrintJobTimeSensor(KEntity, SensorEntity):
    _attr_translation_key = "print_job_time"
    _attr_icon = "mdi:timer-play"
    _attr_native_unit_of_measurement = U_S
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="print_job_time")

    @property
    def native_value(self) -> int | None:
        if self._should_zero():
            return 0
        v = self.coordinator.data.get("printJobTime")
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

class PrintLeftTimeSensor(KEntity, SensorEntity):
    _attr_translation_key = "print_left_time"
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = U_S
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="print_left_time")

    @property
    def native_value(self) -> int | None:
        if self._should_zero():
            return 0
        v = self.coordinator.data.get("printLeftTime")
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None

class RealTimeFlowSensor(KEntity, SensorEntity):
    _attr_translation_key = "real_time_flow"
    _attr_icon = "mdi:cube-send"
    # Use engineering unit mm³/s directly; omit device_class to avoid HA validation warnings.
    _attr_native_unit_of_measurement = "mm³/s"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="real_time_flow")

    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return 0.0
        return _safe_float(self.coordinator.data.get("realTimeFlow"))


class CurrentObjectSensor(KEntity, SensorEntity):
    _attr_translation_key = "current_object"
    _attr_icon = "mdi:cube-outline"

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="current_object")

    @property
    def native_value(self) -> str | None:
        # If printer is off or unavailable, show N/A
        if self._should_zero():
            return "N/A"
        
        d = self.coordinator.data or {}
        v = d.get("current_object") or d.get("currentObject")

        # If no current object and printer is not printing, show "not printing".
        # Firmware may send this as a non-string (e.g. an int object index), so
        # only run the whitespace check on actual strings to avoid AttributeError.
        if not v or (isinstance(v, str) and not v.strip()):
            # Check if printer is actually printing
            fname = d.get("printFileName") or ""
            if not fname:
                return "not printing"
            return None

        return str(v)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data or {}
        return {
            "excluded_objects": d.get("excluded_objects_list", d.get("excluded_objects")),
        }


class ObjectCountSensor(KEntity, SensorEntity):
    _attr_translation_key = "object_count"
    _attr_icon = "mdi:format-list-numbered"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="object_count")

    @property
    def native_value(self) -> int | None:
        # If printer is off or unavailable, show 0
        if self._should_zero():
            return 0
        
        d = self.coordinator.data or {}
        
        # Check if printer is actually printing
        fname = d.get("printFileName") or ""
        if not fname:
            return 0  # "not printing" equivalent for numeric sensor
        
        # Try to get objects data from various possible fields
        objs = d.get("objects_list") or d.get("objectsList") or d.get("objects")
        
        # Handle JSON string format (from diagnostic logs)
        if isinstance(objs, str):
            try:
                parsed_objs = json.loads(objs)
                if isinstance(parsed_objs, list):
                    return len(parsed_objs)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Handle array format
        if isinstance(objs, list):
            return len(objs)
        
        # Handle dict format with list inside
        if isinstance(objs, dict):
            lst = objs.get("list")
            if isinstance(lst, list):
                return len(lst)
        
        return None


class KPrintControlSensor(KEntity, SensorEntity):
    """Diagnostic sensor exposing control pipeline state (queued actions, paused flag, raw states)."""
    _attr_translation_key = "print_control"
    _attr_icon = "mdi:debug-step-over"
    _attr_state_class = None  # not a measurement

    def __init__(self, coordinator):
        super().__init__(coordinator, unique_id="print_control")

    @property
    def native_value(self) -> str | None:
        # Keep state human-readable but stable: "queued" if anything is pending, else "ok".
        if self.coordinator.pending_pause() or self.coordinator.pending_resume():
            return "queued"
        return "ok" if self.coordinator.available else "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data or {}
        return {
            "pending_pause": self.coordinator.pending_pause(),
            "pending_resume": self.coordinator.pending_resume(),
            "paused": self.coordinator.paused_flag(),
            # raw hints (useful for debugging UI logic)
            "status_raw_state": d.get("state"),
            "status_raw_deviceState": d.get("deviceState"),
            "print_file": d.get("printFileName") or "",
            "progress": d.get("printProgress") or d.get("dProgress"),
        }

# ----------------- setup -----------------

class KCFSBoxSensor(KEntity, SensorEntity):
    """Sensor for a CFS Box (Temp/Humidity)."""

    def __init__(self, coordinator, box_id: int, sensor_type: str):
        uid = f"cfs_box_{box_id}_{sensor_type}"
        name = f"CFS Box {box_id} {sensor_type.capitalize()}"
        tk = "cfs_box_temp" if sensor_type == "temp" else "cfs_box_humidity"
        super().__init__(coordinator, name, uid, translation_key=tk)
        self._attr_translation_placeholders = {"box_id": str(box_id)}
        self._box_id = box_id
        self._type = sensor_type  # "temp" or "humidity"
        if sensor_type == "temp":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = U_C
        else:
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = U_PERCENT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_box_data(self) -> dict[str, Any] | None:
        boxes = self.coordinator.data.get("boxsInfo", {}).get("materialBoxs", [])
        for b in boxes:
            if b.get("id") == self._box_id:
                return b
        return None

    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return 0.0
        data = self._get_box_data()
        if data:
            return data.get(self._type)
        return None


def _cfs_slot_attributes(
    data: dict[str, Any],
    box_id: int | None = None,
    slot_id: int | None = None,
) -> dict[str, Any]:
    """Build the shared attribute set for a CFS slot (box slot or external).

    ``box_id``/``slot_id`` are the ids the *printer* uses, which the card needs to
    address the right slot when writing material back via ``set_cfs_material``.
    They are passed in because the raw slot dict only carries its own ``id``, not
    the id of the box it belongs to.
    """
    raw_color = data.get("color")
    return {
        "vendor": data.get("vendor"),
        "type": data.get("type"),
        "name": data.get("name"),
        "color_hex": _normalize_color_hex(raw_color),
        # Kept so the printer's original value stays visible after the
        # leading-pad-character fix (issue #113).
        "color_hex_raw": raw_color,
        "rfid": data.get("rfid"),
        # Derived, stable per material+colour; see utils.build_spool_key (#117).
        "spool_key": _build_spool_key(
            rfid=data.get("rfid"),
            vendor=data.get("vendor"),
            material_type=data.get("type"),
            name=data.get("name"),
            color=raw_color,
        ),
        "state": data.get("state"),
        "selected": data.get("selected"),
        # Addressing + editable material settings, so the CFS card can target the
        # right slot and prefill its edit dialog with the printer's current values.
        "box_id": box_id,
        "slot_id": slot_id,
        "min_temp": _safe_float(data.get("minTemp")),
        "max_temp": _safe_float(data.get("maxTemp")),
        "pressure": _safe_float(data.get("pressure")),
    }


class KCFSSlotSensor(KEntity, SensorEntity):
    """Sensor for a CFS Slot (Filament type/color/percent)."""

    def __init__(self, coordinator, box_id: int, slot_id: int, sensor_type: str):
        uid = f"cfs_box_{box_id}_slot_{slot_id}_{sensor_type}"
        type_label = sensor_type.replace("_", " ").capitalize()
        name = f"CFS Box {box_id} Slot {slot_id + 1} {type_label}"
        tk = f"cfs_slot_{sensor_type}"
        super().__init__(coordinator, name, uid, translation_key=tk)
        self._attr_translation_placeholders = {"box_id": str(box_id), "slot": str(slot_id + 1)}
        self._box_id = box_id
        self._slot_id = slot_id
        self._type = sensor_type  # "filament", "color", "percent"
        
        if sensor_type == "percent":
            self._attr_native_unit_of_measurement = U_PERCENT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "color":
            self._attr_icon = "mdi:palette"

    def _get_slot_data(self) -> dict[str, Any] | None:
        boxes = self.coordinator.data.get("boxsInfo", {}).get("materialBoxs", [])
        for b in boxes:
            if b.get("id") == self._box_id:
                materials = b.get("materials", [])
                for m in materials:
                    if m.get("id") == self._slot_id:
                        return m
        return None

    @property
    def native_value(self) -> Any:
        if self._should_zero():
            return 0 if self._type == "percent" else "N/A"
            
        data = self._get_slot_data()
        if not data:
            return None
            
        if self._type == "filament":
            return _format_filament_label(
                data.get("vendor"), data.get("name"), data.get("type")
            )
        if self._type == "color":
            return _normalize_color_hex(data.get("color"))
        if self._type == "percent":
            return data.get("percent")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # native_value already zeroes here; publishing the last-known material
        # alongside a zeroed state is worse than publishing nothing, because the
        # card builds its edit payload out of these attributes.
        if self._should_zero():
            return {}
        data = self._get_slot_data()
        if not data:
            return {}
        return _cfs_slot_attributes(data, self._box_id, self._slot_id)


class KCFSExtSlotSensor(KEntity, SensorEntity):
    """Sensor for the External Filament slot (Filament type/color/percent)."""

    def __init__(self, coordinator, slot_id: int, sensor_type: str):
        uid = f"cfs_external_{sensor_type}"
        type_label = sensor_type.replace("_", " ").capitalize()
        name = f"CFS External {type_label}"
        tk = f"cfs_ext_{sensor_type}"
        super().__init__(coordinator, name, uid, translation_key=tk)
        self._slot_id = slot_id
        self._type = sensor_type

        if sensor_type == "percent":
            self._attr_native_unit_of_measurement = U_PERCENT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "color":
            self._attr_icon = "mdi:palette"

    def _get_external_box(self) -> dict[str, Any] | None:
        boxes = self.coordinator.data.get("boxsInfo", {}).get("materialBoxs", [])
        for b in boxes:
            if b.get("type") == 1:
                return b
        return None

    def _get_slot_data(self) -> dict[str, Any] | None:
        box = self._get_external_box()
        if not box:
            return None
        materials = box.get("materials", [])
        for m in materials:
            if m.get("id") == self._slot_id:
                return m
        return materials[0] if materials else None

    @property
    def native_value(self) -> Any:
        if self._should_zero():
            return 0 if self._type == "percent" else "N/A"

        data = self._get_slot_data()
        if not data:
            return None

        if self._type == "filament":
            return _format_filament_label(
                data.get("vendor"), data.get("name"), data.get("type")
            )
        if self._type == "color":
            return _normalize_color_hex(data.get("color"))
        if self._type == "percent":
            return data.get("percent")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._should_zero():
            return {}
        data = self._get_slot_data()
        if not data:
            return {}
        # The external box's id is whatever the printer reports for the type==1
        # box, so read it back rather than assuming 0.
        box = self._get_external_box() or {}
        return _cfs_slot_attributes(data, box.get("id"), data.get("id", self._slot_id))


class KActiveFilamentSensor(KEntity, SensorEntity):
    """Sensor reporting which CFS slot or external filament is currently selected."""

    def __init__(self, coordinator):
        super().__init__(coordinator, "", "active_filament_slot", translation_key="active_filament_slot")
        self._attr_icon = "mdi:printer-3d-nozzle"

    @property
    def native_value(self) -> str | None:
        if self._should_zero():
            return None
        data = self.coordinator.data or {}
        boxes = data.get("boxsInfo", {}).get("materialBoxs", [])
        for box in boxes:
            box_type = box.get("type", 0)
            for slot in box.get("materials", []):
                if slot.get("selected"):
                    if box_type == 1:
                        return "External"
                    slot_id = slot.get("id", 0)
                    box_id = box.get("id", 0)
                    return f"Box {box_id} Slot {slot_id + 1}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._should_zero():
            return {}
        data = self.coordinator.data or {}
        boxes = data.get("boxsInfo", {}).get("materialBoxs", [])
        for box in boxes:
            for slot in box.get("materials", []):
                if slot.get("selected"):
                    return {
                        "filament": _format_filament_label(
                            slot.get("vendor"), slot.get("name"), slot.get("type")
                        ),
                        "color": _normalize_color_hex(slot.get("color")),
                        "percent": slot.get("percent"),
                    }
        return {}


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up sensor platform for entry: %s", entry.entry_id)
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list[SensorEntity] = []

    # Track which CFS entities we've already added to avoid duplicates
    added_cfs_uids: set[str] = set()

    def add_cfs_entities():
        """Helper to create CFS entities from current data."""
        new_ents = []
        cfs_data = coord.data.get("boxsInfo", {})
        
        if not cfs_data:
            _LOGGER.debug("add_cfs_entities: No boxsInfo in coordinator data")
            return []

        material_boxes = cfs_data.get("materialBoxs", [])
        _LOGGER.debug("add_cfs_entities processing %d materialBoxs", len(material_boxes))
        
        has_cfs_box = any(box.get("type") == 0 for box in material_boxes)
        external_box = next((box for box in material_boxes if box.get("type") == 1), None)
        
        for box in material_boxes:
            box_id = box.get("id")
            if box_id is None:
                _LOGGER.debug("Skipping box with no ID: %s", box)
                continue
            if has_cfs_box and box.get("type") == 1:
                _LOGGER.debug("Skipping external box (type 1) because CFS (type 0) is present")
                continue

            
            # Box sensors
            for s_type in ("temp", "humidity"):
                if box.get(s_type) is not None:
                    uid = f"cfs_box_{box_id}_{s_type}"
                    if uid not in added_cfs_uids:
                        new_ents.append(KCFSBoxSensor(coord, box_id, s_type))
                        added_cfs_uids.add(uid)
                        _LOGGER.debug("Registered new CFS UID: %s", uid)
                    else:
                         _LOGGER.debug("Skipping existing CFS UID: %s", uid)
                
            # Slots
            for idx, slot in enumerate(box.get("materials", [])):
                slot_id = slot.get("id")
                try:
                    slot_id = int(slot_id) if slot_id is not None else None
                except (TypeError, ValueError):
                    slot_id = None
                if slot_id is None or slot_id < 0:
                    slot_id = idx
                for s_type in ("filament", "color", "percent"):
                    uid = f"cfs_box_{box_id}_slot_{slot_id}_{s_type}"
                    if uid not in added_cfs_uids:
                        new_ents.append(KCFSSlotSensor(coord, box_id, slot_id, s_type))
                        added_cfs_uids.add(uid)
                        _LOGGER.debug("Registered new CFS Slot UID: %s", uid)
                    else:
                        _LOGGER.debug("Skipping existing CFS Slot UID: %s", uid)

        if external_box:
            materials = external_box.get("materials", [])
            if materials:
                slot_id = materials[0].get("id", 0)
                for s_type in ("filament", "color", "percent"):
                    uid = f"cfs_external_{s_type}"
                    if uid not in added_cfs_uids:
                        new_ents.append(KCFSExtSlotSensor(coord, slot_id, s_type))
                        added_cfs_uids.add(uid)
                        _LOGGER.debug("Registered new CFS External UID: %s", uid)
                    else:
                        _LOGGER.debug("Skipping existing CFS External UID: %s", uid)
            else:
                _LOGGER.debug("External box found but has no materials")

        # Active filament slot sensor (one per printer, added once)
        active_uid = "active_filament_slot"
        if active_uid not in added_cfs_uids:
            new_ents.append(KActiveFilamentSensor(coord))
            added_cfs_uids.add(active_uid)
            _LOGGER.debug("Registered new CFS UID: %s", active_uid)

        _LOGGER.debug("add_cfs_entities prepared %d new entities. Total tracked UIDs: %d", len(new_ents), len(added_cfs_uids))
        return new_ents


    # `call_soon` cannot be cancelled, and disconnecting the dispatcher does not
    # unschedule a callback that is already queued. Without this flag the
    # deferred `async_add_entities` could run against an unloaded entry.
    platform_live = True

    def _mark_unloaded() -> None:
        nonlocal platform_live
        platform_live = False

    entry.async_on_unload(_mark_unloaded)

    def _add_if_live(new_ents: list[SensorEntity]) -> None:
        if platform_live:
            async_add_entities(new_ents)

    added_chamber_uids: set[str] = set()

    def add_chamber_entities() -> list[SensorEntity]:
        """Chamber sensors not yet created, re-evaluated on every call.

        Capability is read fresh rather than captured at setup: a printer that was
        off during setup reports boxTemp/maxBoxTemp later, and the discovery
        signal is what brings us back here. Returning [] and never being asked
        again left the sensors missing for the whole session.
        """
        has_chamber = entry.data.get(
            "_cached_has_chamber_sensor", entry.data.get("_cached_has_box_sensor", False)
        )
        live = coord.data or {}
        if not has_chamber and any(
            k in live for k in ("boxTemp", "targetBoxTemp", "maxBoxTemp")
        ):
            has_chamber = True
        if not has_chamber:
            return []

        out: list[SensorEntity] = []
        if "box_temperature" not in added_chamber_uids:
            for spec in SPECS:
                if spec.get("uid") == "box_temperature":
                    added_chamber_uids.add("box_temperature")
                    out.append(KSimpleFieldSensor(coord, spec))
                    break

        if "max_box_temp" not in added_chamber_uids:
            max_box = entry.data.get(
                "_cached_max_chamber_temp", entry.data.get("_cached_max_box_temp")
            )
            if max_box is None:
                max_box = live.get("maxBoxTemp")
            if max_box is not None:
                added_chamber_uids.add("max_box_temp")
                out.append(
                    KMaxTempSensor(
                        coord, uid="max_box_temp", key="max_box_temp",
                        translation_key="max_chamber_temp",
                    )
                )
        return out

    added_gcode_uids: set[str] = set()

    def add_gcode_info_entities() -> list[SensorEntity]:
        """Sensors for the slicer's estimates, once the printer has supplied any.

        Gated rather than unconditional because firmware without the metadata
        request simply never answers it, and three permanently-unknown entities
        are a worse answer than none. The key only appears once a real entry has
        been matched to a job, so its presence is the printer's yes.
        """
        if GCODE_INFO_KEY not in (coord.data or {}):
            return []

        out: list[SensorEntity] = []
        for uid, cls in (
            ("expected_material_length", ExpectedMaterialLengthSensor),
            ("expected_material_weight", ExpectedMaterialWeightSensor),
            ("filament_consumption", FilamentConsumptionSensor),
        ):
            if uid not in added_gcode_uids:
                added_gcode_uids.add(uid)
                out.append(cls(coord))
        return out

    # Dynamic CFS entity handler
    # The dispatcher runs a plain sync target in an executor thread, and this
    # calls `hass.loop.call_soon`, which is not thread-safe. Cheap enough to
    # belong on the loop.
    @callback
    def _on_new_entities() -> None:
        """Handle signal for new entities (e.g. late CFS discovery)."""
        _LOGGER.debug("Dynamic entity signal received, checking for new CFS entities...")
        new_ents = (
            add_cfs_entities() + add_chamber_entities() + add_gcode_info_entities()
        )
        if new_ents:
            _LOGGER.debug("Adding %d dynamic entities", len(new_ents))
            # Must not be called inline from the dispatcher: async_add_entities
            # eager-starts a task on the config entry, and doing that from inside
            # the dispatch chain leaves it unreferenced ("Task was destroyed but
            # it is pending"), so no entities get added. Deferring to the next
            # loop iteration schedules it in a normal context.
            hass.loop.call_soon(_add_if_live, new_ents)
    
    # Listen for the signal fired by coordinator
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, 
            f"{DOMAIN}_new_entities_{entry.entry_id}", 
            _on_new_entities
        )
    )

    
    # Core sensors
    ents.append(PrintStatusSensor(coord))
    ents.append(UsedMaterialLengthSensor(coord))
    ents.append(PrintJobTimeSensor(coord))
    ents.append(PrintLeftTimeSensor(coord))
    ents.append(RealTimeFlowSensor(coord))
    ents.append(CurrentObjectSensor(coord))
    ents.append(ObjectCountSensor(coord))
    ents.append(KPrintControlSensor(coord))
    
    # The printer's identity. Deliberately not a SPECS row: SPECS is for
    # telemetry fields, and this is static. A second, byte-identical copy of
    # this sensor used to live there under the uid "system"; it was retired
    # in favour of this one, whose name says what the value is.
    ents.append(KSimpleFieldSensor(
        coord,
        {
            "uid": "model_info",
            "name": "Model",
            "translation_key": "model_info",
            "field": "model",
            "device_class": None,
            "unit": None,
            "state_class": None,
            "attrs": lambda d: _attr_dict(
                ("hostname", d.get("hostname")),
                ("modelVersion", d.get("modelVersion")),
            )
        }
    ))


    # Chamber sensors come from add_chamber_entities() so the late-discovery pass
    # applies the identical gate; everything else is unconditional.
    for spec in SPECS:
        if spec.get("uid") != "box_temperature":
            ents.append(KSimpleFieldSensor(coord, spec))

    # Mapped sensors
    for spec in MAPPED_SPECS:
        ents.append(KMappedSensor(coord, spec))

    # Additional metrics

    # --- Max temperature sensors (non-editable, from cached/live capability limits) ---
    # Pull cached values first
    cached = coord.config_entry.data if coord.config_entry else None

    def _cached_or_live(key: str):
        """The cached limit, or the live one when the cache has no value for it.

        Per field, matching `KMaxTempSensor._read_cached_or_live` and
        `add_chamber_entities`. The cache writer always *writes* these keys --
        `d.get("maxBedTemp", <previous>)` -- so a key can be present and `None`,
        and keying the fallback on presence alone meant this gate returned that
        `None` and skipped creating the sensor for the rest of the session, even
        though the entity itself would have served the live value.
        """
        d = coord.data or {}
        if key == "max_bed_temp":
            live = d.get("maxBedTemp")
            cached_value = cached.get("_cached_max_bed_temp") if cached else None
        elif key == "max_nozzle_temp":
            live = d.get("maxNozzleTemp")
            cached_value = cached.get("_cached_max_nozzle_temp") if cached else None
        elif key == "max_box_temp":
            live = d.get("maxBoxTemp")
            cached_value = (
                cached.get("_cached_max_chamber_temp", cached.get("_cached_max_box_temp"))
                if cached else None
            )
        else:
            return None
        return cached_value if cached_value is not None else live

    max_noz = _cached_or_live("max_nozzle_temp")
    max_bed = _cached_or_live("max_bed_temp")

    if max_noz is not None:
        ents.append(KMaxTempSensor(coord, uid="max_nozzle_temp", key="max_nozzle_temp", translation_key="max_nozzle_temp"))
    if max_bed is not None:
        ents.append(KMaxTempSensor(coord, uid="max_bed_temp", key="max_bed_temp", translation_key="max_bed_temp"))
    # Chamber max is gated with the chamber temperature sensor, in one place.
    ents.extend(add_chamber_entities())
    ents.extend(add_gcode_info_entities())

    # Register static entities immediately
    try:
        async_add_entities(ents)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Failed to add static sensors: %s", err)
        # Both helpers marked their uids before handing the entities over, so a
        # failure here would otherwise make every later discovery pass return []
        # and those sensors would stay missing for the whole session.
        added_chamber_uids.clear()
        added_gcode_uids.clear()

    # --- CFS Entities (Dynamic Initial Load) ---
    try:
        cfs_ents = add_cfs_entities()
        if cfs_ents:
            async_add_entities(cfs_ents)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Failed to add initial CFS sensors: %s", err)




class KMaxTempSensor(KEntity, SensorEntity):
    """Non-editable sensor exposing maximum temperature limits from device telemetry/cache.

    Does not zero when the printer is off/unavailable; similar to the System model sensor behavior.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, uid: str, key: str, translation_key: str):
        super().__init__(coordinator, "", uid, translation_key=translation_key)
        self._key = key  # one of: max_nozzle_temp, max_bed_temp, max_box_temp
        self._attr_native_unit_of_measurement = U_C

    @property
    def available(self) -> bool:
        # Max temp sensors are configuration constants, always available
        return True

    def _read_cached_or_live(self) -> float | None:
        """The cached capability constant, or the live one when it is missing.

        Per *field*: `_device_info_cached` is set as soon as the model is known,
        while `maxBoxTemp` arrives by late discovery, so an entry can carry the
        flag with no chamber max in it. Returning the cached `None` there hid a
        value the printer was already reporting.
        """
        # Live telemetry, used as the fallback for whichever field is uncached.
        d = self.coordinator.data or {}
        if self._key == "max_nozzle_temp":
            live = d.get("maxNozzleTemp")
        elif self._key == "max_bed_temp":
            live = d.get("maxBedTemp")
        elif self._key == "max_box_temp":
            live = d.get("maxBoxTemp")
        else:
            return None

        entry = self.coordinator.config_entry
        if entry and entry.data.get("_device_info_cached"):
            if self._key == "max_nozzle_temp":
                cached = entry.data.get("_cached_max_nozzle_temp")
            elif self._key == "max_bed_temp":
                cached = entry.data.get("_cached_max_bed_temp")
            else:
                # Prefer the chamber cache, falling back to the legacy box one
                # for entries cached by a pre-rename release.
                cached = entry.data.get(
                    "_cached_max_chamber_temp", entry.data.get("_cached_max_box_temp")
                )
            if cached is not None:
                return cached

        return live

    @property
    def native_value(self) -> float | None:
        # Do NOT zero when printer is off; these are capability constants
        v = self._read_cached_or_live()
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None
