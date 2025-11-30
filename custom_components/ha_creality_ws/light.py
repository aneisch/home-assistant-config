from __future__ import annotations

from homeassistant.components.light import LightEntity, ColorMode  # type: ignore[import]

from .const import DOMAIN
from .entity import KEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]

    # Only expose if model supports light or if live data shows the field
    has_light = entry.data.get("_cached_has_light", True)
    if not has_light and "lightSw" in (coord.data or {}):
        has_light = True

    if not has_light:
        async_add_entities([])
        return

    async_add_entities([_KLight(coord)])


class _KLight(KEntity, LightEntity):
    _attr_name = "Light"
    _attr_icon = "mdi:lightbulb"
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    # Native light entity should be enabled by default
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, self._attr_name, "light")

    @property
    def is_on(self) -> bool | None:
        if self._should_zero():
            return False
        val = self.coordinator.data.get("lightSw")
        return bool(val) if val is not None else False

    async def async_turn_on(self, **kwargs):
        await self.coordinator.client.send_set_retry(lightSw=1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.client.send_set_retry(lightSw=0)
