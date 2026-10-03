from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature  # type: ignore[import]

from .const import DOMAIN
from .entity import KEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]

    ents: list[FanEntity] = []
    # Three controllable fans exposed by telemetry and gcode M106 channels
    ents.append(_KFanEntity(coord, name="Model Fan", read_field="modelFanPct", uid="model_fan", channel=0, translation_key="model_fan"))
    ents.append(_KFanEntity(coord, name="Case Fan", read_field="caseFanPct", uid="case_fan", channel=1, translation_key="case_fan"))
    ents.append(_KFanEntity(coord, name="Side Fan", read_field="auxiliaryFanPct", uid="side_fan", channel=2, translation_key="side_fan"))

    async_add_entities(ents)


class _KFanEntity(KEntity, FanEntity):
    """A simple percentage-based fan mapped to M106 Px Syyy."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )
    _attr_percentage_step = 1

    # New native fan entities should be enabled by default; keep old Number entities for BC
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator, name: str, read_field: str, uid: str, channel: int, translation_key: str | None = None) -> None:
        super().__init__(coordinator, name, uid, translation_key=translation_key)
        self._read_field = read_field
        self._channel = int(channel)

    # Availability is controlled by base KEntity (always available, but may zero)

    @property
    def is_on(self) -> bool:
        if self._should_zero():
            return False
        pct = self.percentage or 0
        try:
            return float(pct) > 0
        except Exception:
            return False

    @property
    def percentage(self) -> int | None:
        if self._should_zero():
            return 0
        v = self.coordinator.data.get(self._read_field)
        try:
            return int(round(float(v))) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    async def async_set_percentage(self, percentage: int) -> None:
        pct = max(0, min(100, int(round(percentage))))
        s_val = int(round(255 * (pct / 100.0)))
        cmd = f"M106 P{self._channel} S{s_val}"
        await self.coordinator.client.send_set_retry(gcodeCmd=cmd)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn the fan on, at the requested percentage if one was given.

        With no percentage, restore whatever the fan was last running at, or go
        to full -- turning a fan "on" to 0% would be indistinguishable from off.
        """
        pct: int | None = None
        if percentage is not None:
            try:
                pct = int(round(float(percentage)))
            except (TypeError, ValueError):
                pct = None

        if pct is None:
            current = self.percentage or 0
            pct = current if current > 0 else 100

        await self.async_set_percentage(pct)

    async def async_turn_off(self, **kwargs) -> None:  # type: ignore[override]
        await self.async_set_percentage(0)
