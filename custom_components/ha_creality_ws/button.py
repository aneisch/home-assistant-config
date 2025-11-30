from __future__ import annotations

import asyncio
import logging
from homeassistant.components.button import ButtonEntity

from .entity import KEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        KHomeAllButton(coord),
        KPrintPauseButton(coord),
        KPrintResumeButton(coord),
        KPrintStopButton(coord),
    ])

class KHomeAllButton(KEntity, ButtonEntity):
    _attr_name = "Home (XY then Z)"
    _attr_icon = "mdi:home-circle"

    def __init__(self, coordinator):
        super().__init__(coordinator, self._attr_name, "home_all")
        self._seq_lock = asyncio.Lock()

    async def async_press(self) -> None:
        async with self._seq_lock:
            # Ensure WebSocket connection is active before sending commands
            if not await self.coordinator.ensure_connected():
                _LOGGER.warning("Cannot execute home command: printer not connected")
                return
            await self.coordinator.client.send_set_retry(autohome="X Y")
            await asyncio.sleep(1.0)
            await self._wait_until_idle_or_timeout(15.0)
            await self.coordinator.client.send_set_retry(autohome="Z")

    async def _wait_until_idle_or_timeout(self, timeout: float) -> None:
        end = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end:
            if (self.coordinator.data or {}).get("deviceState") != 7:
                return
            await asyncio.sleep(0.25)

class _BasePrintButton(KEntity, ButtonEntity):
    _attr_icon = "mdi:printer-3d"
    def __init__(self, coordinator, name: str, uid: str):
        super().__init__(coordinator, name, uid)

class KPrintPauseButton(_BasePrintButton):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Pause Print", "pause_print")
    async def async_press(self) -> None:
        await self.coordinator.request_pause()  # no optimistic mark

class KPrintResumeButton(_BasePrintButton):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Resume Print", "resume_print")
    async def async_press(self) -> None:
        await self.coordinator.request_resume()  # no optimistic mark

class KPrintStopButton(_BasePrintButton):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Stop Print", "stop_print")
    async def async_press(self) -> None:
        # Ensure WebSocket connection is active before sending commands
        if not await self.coordinator.ensure_connected():
            _LOGGER.warning("Cannot execute stop command: printer not connected")
            return
        await self.coordinator.client.send_set_retry(stop=1)
        # don't force paused flag here; telemetry will reflect idle soon
