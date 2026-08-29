from __future__ import annotations

from typing import Any

from homeassistant.components.light import (  # type: ignore[import]
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)

from .const import DOMAIN
from .entity import KEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]

    # Only expose if model supports light or if live data shows the field
    has_light = entry.data.get("_cached_has_light", True)
    has_brightness_control = entry.data.get("_cached_has_brightness_control", False)
    if not has_light and "lightSw" in (coord.data or {}):
        has_light = True

    if not has_light:
        async_add_entities([])
        return

    led_pin = entry.data.get("_cached_led_pin") if has_brightness_control else None
    # Model claims brightness control but no LED pin is cached: we have no way to
    # dim it, so fall back to a plain on/off light.
    if has_brightness_control and not led_pin:
        has_brightness_control = False

    async_add_entities(
        [_KLight(coord, has_brightness_control=has_brightness_control, led_pin=led_pin)]
    )


class _KLight(KEntity, LightEntity):
    _attr_translation_key = "light"
    _attr_icon = "mdi:lightbulb"

    # Native light entity should be enabled by default
    _attr_entity_registry_enabled_default = True

    def __init__(self, coordinator, *, has_brightness_control: bool = False, led_pin: str | None = None) -> None:
        super().__init__(coordinator, unique_id="light")
        self._has_brightness_control = has_brightness_control
        # Klipper output_pin name for SET_PIN dimming; None when the model has no
        # brightness control (so we never hijack a pin).
        self._led_pin = led_pin if has_brightness_control else None
        if has_brightness_control:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
        # This firmware reports lightSw only as 0/1 (on/off), not the dim level,
        # so remember the last set brightness to report it back to HA.
        self._brightness: int | None = None

    def _is_on(self) -> bool:
        """Return whether the LED is on, based on the lightSw switch (0/1).
        Returns False if the switch is missing or invalid."""
        if self._should_zero():
            return False
        val = self.coordinator.data.get("lightSw")
        if val is None:
            return False
        try:
            return float(val) > 0
        except (TypeError, ValueError):
            return False

    @property
    def is_on(self) -> bool | None:
        return self._is_on()

    @property
    def brightness(self) -> int | None:
        if not self._has_brightness_control:
            return None
        if not self._is_on():
            return None
        # This firmware never reports the dim level, so report the remembered
        # value (or full brightness if we never set one).
        return self._brightness if self._brightness is not None else 255

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light, optionally setting its brightness."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is None or not self._led_pin:
            # Plain on: the lightSw switch turns the LED to full brightness.
            await self.coordinator.client.send_set_retry(lightSw=1)
            self._brightness = 255
            self.async_write_ha_state()
            return

        b = max(0, min(255, int(brightness)))
        if b <= 0:
            await self.async_turn_off()
            return

        # SET_PIN (Klipper) sets the real PWM level but does NOT update the
        # Creality lightSw state. Send lightSw=1 first so on/off telemetry stays
        # in sync, then apply the dim level. Telemetry never reports the level,
        # so remember it to report brightness back to HA.
        await self.coordinator.client.send_set_retry(lightSw=1)
        value = round(b / 255, 4)
        await self.coordinator.client.send_set_retry(gcodeCmd=f"SET_PIN PIN={self._led_pin} VALUE={value}")
        self._brightness = b
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.client.send_set_retry(lightSw=0)
