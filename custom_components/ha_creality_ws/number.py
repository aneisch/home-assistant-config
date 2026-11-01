from __future__ import annotations

import logging

from homeassistant.core import callback  # type: ignore[import]
from homeassistant.components.number import NumberEntity, NumberMode, NumberDeviceClass

from homeassistant.const import (  # type: ignore[import]
    PERCENTAGE as UNIT_PERCENT,
    UnitOfTemperature,
)

UNIT_CELSIUS = UnitOfTemperature.CELSIUS

from homeassistant.helpers.dispatcher import async_dispatcher_connect  # type: ignore[import]
from .const import DOMAIN
from .entity import KEntity
from .utils import ModelDetection

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the number entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list[NumberEntity] = []

    # Standard entities for all printers
    ents.append(PrintTuningPercent(coord))
    ents.append(FlowRatePercent(coord))
    ents.append(NozzleTargetNumber(coord))
    ents.append(BedTargetNumber(coord, bed_index=0))

    # Chamber temperature control (K2 family; never the K1 family, R71).
    #
    # This used to be gated purely on live `maxBoxTemp`, which the printer only
    # reports once it is reachable. Platform setup deliberately does not wait for
    # the printer, so a Home Assistant restart while the printer was off left the
    # entity uncreated -- and nothing recreated it when the printer came back, so
    # it stayed `unavailable` until the next restart that happened to win the
    # race. It is now satisfied by the capability cached during onboarding, and
    # created late via the discovery signal if neither is available yet.
    added: set[str] = set()

    def _chamber_entities() -> list[NumberEntity]:
        if "box_target" in added:
            return []
        # No K1-family printer has a chamber heater, although a K1C reports
        # targetBoxTemp; the control it got that way did nothing (R71).
        if ModelDetection.from_cache(entry.data, coord.data).is_k1_family:
            return []
        # Read the capability on every call rather than capturing it at setup:
        # the late pass has to see the current entry data, and live telemetry
        # promotes the capability the same way __init__ does when caching it.
        has_box_control = entry.data.get(
            "_cached_has_chamber_control", entry.data.get("_cached_has_box_control", False)
        )
        # `targetBoxTemp` only, matching the promotion in __init__.py: there,
        # `maxBoxTemp` promotes the chamber *sensor* (:317) and only
        # `targetBoxTemp` promotes the *control* (:314). Accepting `maxBoxTemp`
        # here conflated the two, so a K1-family printer -- chamber sensor, no
        # chamber control, and it does report a maximum -- was given a target
        # control whose setter sends a `boxTempControl` it cannot honour.
        if not has_box_control and "targetBoxTemp" in coord.data:
            has_box_control = True
        if not has_box_control:
            return []
        # A printer reporting targetBoxTemp has a settable chamber whether or not
        # it also reports a maximum, and BoxTargetNumber already falls back to
        # 60 C. Requiring a max here consumed the discovery signal and then left
        # the control absent for good.
        if "targetBoxTemp" in coord.data:
            added.add("box_target")
            return [BoxTargetNumber(coord)]
        cached_max = entry.data.get(
            "_cached_max_chamber_temp", entry.data.get("_cached_max_box_temp")
        )
        if not coord.data.get("maxBoxTemp") and not cached_max:
            return []
        added.add("box_target")
        return [BoxTargetNumber(coord)]

    ents.extend(_chamber_entities())

    # `call_soon` cannot be cancelled, and disconnecting the dispatcher does not
    # unschedule a callback that is already queued. Without this flag the
    # deferred `async_add_entities` could run against an unloaded entry.
    platform_live = True

    def _mark_unloaded() -> None:
        nonlocal platform_live
        platform_live = False

    entry.async_on_unload(_mark_unloaded)

    def _add_if_live(new_ents: list[NumberEntity]) -> None:
        if platform_live:
            async_add_entities(new_ents)

    # The dispatcher runs a plain sync target in an executor thread, and this
    # calls `hass.loop.call_soon`, which is not thread-safe. Cheap enough to
    # belong on the loop.
    @callback
    def _on_new_entities() -> None:
        """Late discovery: the printer has just reported a gating field."""
        new_ents = _chamber_entities()
        if new_ents:
            _LOGGER.debug("Adding %d late-discovered number entities", len(new_ents))
            # Deferred, not inline: see the matching note in sensor.py.
            hass.loop.call_soon(_add_if_live, new_ents)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_new_entities_{entry.entry_id}",
            _on_new_entities,
        )
    )

    async_add_entities(ents)


# ---------- Unified speed+flow percent ----------
class PrintTuningPercent(KEntity, NumberEntity):
    """Print speed, as a percentage of the sliced speed.

    Writes setFeedratePct only. It used to write the flow rate as well, "in
    lockstep", so 150% speed also meant 150% extrusion (R26); flow is now its
    own number. The unique id keeps its old name so the entity is not orphaned.
    """
    _attr_translation_key = "print_tuning_pct"
    _attr_icon = "mdi:speedometer"
    _attr_native_unit_of_measurement = UNIT_PERCENT
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 1.0
    _attr_native_max_value = 200.0
    _attr_native_step = 1.0
    _field = "curFeedratePct"
    _command = "setFeedratePct"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, unique_id="print_tuning_pct")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self._should_zero():
            return None
        v = self.coordinator.data.get(self._field)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        v = int(max(self._attr_native_min_value, min(self._attr_native_max_value, round(value))))
        await self._send(**{self._command: v})


class FlowRatePercent(PrintTuningPercent):
    """The extrusion flow rate, as a percentage (R26)."""
    _attr_translation_key = "flow_rate_pct"
    _attr_icon = "mdi:printer-3d-nozzle-outline"
    _field = "curFlowratePct"
    _command = "setFlowratePct"

    def __init__(self, coordinator) -> None:
        KEntity.__init__(self, coordinator, unique_id="flow_rate_pct")


# ---------- Temperature targets (BOX inputs) ----------
class NozzleTargetNumber(KEntity, NumberEntity):
    _attr_translation_key = "nozzle_target"
    _attr_icon = "mdi:thermometer"
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UNIT_CELSIUS
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_min_value = 0.0
    _attr_native_step = 1.0

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, unique_id="nozzle_target")
        # Use cached max temperature value with fallback to live data
        max_temps = self._get_cached_max_temps()
        max_nozzle_temp = max_temps.get("max_nozzle_temp")
        self._attr_native_max_value = float(max_nozzle_temp) if max_nozzle_temp is not None else 300.0
    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return None
        v = self.coordinator.data.get("targetNozzleTemp")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        v = int(round(value))
        v = max(int(self._attr_native_min_value or 0), v)
        max_v = self._attr_native_max_value
        if max_v is not None:
            v = min(int(max_v), v)

        # Sent first: a target the printer never received must not show (R32).
        before = self.coordinator.client.reported("targetNozzleTemp")
        await self._send(nozzleTempControl=v)
        self.coordinator.assume_commanded(
            {"targetNozzleTemp": v}, reported_before={"targetNozzleTemp": before}
        )


class BedTargetNumber(KEntity, NumberEntity):
    _attr_translation_key = "bed_target"
    _attr_icon = "mdi:radiator"
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UNIT_CELSIUS
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_min_value = 0.0
    _attr_native_step = 1.0

    def __init__(self, coordinator, bed_index: int = 0) -> None:
        super().__init__(coordinator, unique_id=f"bed_target_{bed_index}")
        self._idx = int(bed_index)
        # Use cached max temperature value with fallback to live data
        max_temps = self._get_cached_max_temps()
        max_bed_temp = max_temps.get("max_bed_temp")
        self._attr_native_max_value = float(max_bed_temp) if max_bed_temp is not None else 100.0

    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return None
        v = self.coordinator.data.get(f"targetBedTemp{self._idx}")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        v = int(round(value))
        v = max(int(self._attr_native_min_value or 0), v)
        max_v = self._attr_native_max_value
        if max_v is not None:
            v = min(int(max_v), v)

        key = f"targetBedTemp{self._idx}"
        before = self.coordinator.client.reported(key)
        await self._send(bedTempControl={"num": self._idx, "val": v})
        self.coordinator.assume_commanded({key: v}, reported_before={key: before})


class BoxTargetNumber(KEntity, NumberEntity):
    _attr_translation_key = "chamber_target"
    _attr_icon = "mdi:thermometer"
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UNIT_CELSIUS
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_min_value = 0.0
    _attr_native_step = 1.0

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, unique_id="box_target")
        # Use cached max temperature value with fallback to live data
        max_temps = self._get_cached_max_temps()
        max_box_temp = max_temps.get("max_box_temp")
        
        # Handle printers without heated chamber (maxBoxTemp is None)
        if max_box_temp is None:
            # Default to 60°C for printers with box sensor but no heated chamber
            max_box_temp = 60
        elif not isinstance(max_box_temp, (int, float)):
            # Fallback for invalid values
            max_box_temp = 60
            
        self._attr_native_max_value = float(max_box_temp)
    @property
    def native_value(self) -> float | None:
        if self._should_zero():
            return None
        v = self.coordinator.data.get("targetBoxTemp")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        v = int(round(value))

        v = max(int(self._attr_native_min_value or 0), v)
        max_v = self._attr_native_max_value
        if max_v is not None:
            v = min(int(max_v), v)

        before = self.coordinator.client.reported("targetBoxTemp")
        await self._send(boxTempControl=v)
        # Optimistic update, which goes through merge_telemetry: targetBoxTemp
        # is a LATE_DISCOVERY_FIELDS entry, and writing it straight into .data
        # consumes the one-shot that other gates depend on.
        self.coordinator.assume_commanded(
            {"targetBoxTemp": v}, reported_before={"targetBoxTemp": before}
        )
