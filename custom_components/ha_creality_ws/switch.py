from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers import entity_registry as er  # type: ignore[import]

from .entity import KEntity
from .const import DOMAIN

# Switch mappings (fans controlled via number entities, not switches)
MAP = {
    "light": ("Light", "lightSw"),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    
    # Light switch only if model supports it
    has_light = entry.data.get("_cached_has_light", True)
    if not has_light:
        # Fallback: if telemetry already exposes lightSw field, allow switch.
        if "lightSw" in (coord.data or {}):
            has_light = True
    
    ents = []
    for key, (name, field) in MAP.items():
        if key == "light" and not has_light:
            continue
        # Only create the legacy light switch if it already exists in the registry (migration safety)
        if key == "light":
            reg = er.async_get(hass)
            legacy_uid = f"{coord.client._host}-light"
            existing = reg.async_get_entity_id("switch", DOMAIN, legacy_uid)
            if not existing:
                # No legacy switch to migrate; skip creating to avoid duplicate with new light entity
                continue
        ents.append(KSimpleSwitch(coord, name, field, key))
    
    async_add_entities(ents)


class KSimpleSwitch(KEntity, SwitchEntity):
    _attr_icon = "mdi:toggle-switch"
    # Keep legacy light switch but disable by default in registry now that native light exists
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, name: str, field: str, unique_id: str):
        super().__init__(coordinator, name, unique_id)
        self._field = field

    @property
    def is_on(self) -> bool:
        if self._should_zero():
            return False
        val = self.coordinator.data.get(self._field)
        return bool(val) if val is not None else False

    async def async_turn_on(self, **kwargs):
        await self.coordinator.client.send_set_retry(**{self._field: 1})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.client.send_set_retry(**{self._field: 0})