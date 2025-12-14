from __future__ import annotations
import logging
import asyncio
from typing import Any, Iterable
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .ws_client import KClient
from .const import DOMAIN, STALE_AFTER_SECS

_LOGGER = logging.getLogger(__name__)


class KCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, host: str, power_switch: str | None = None):
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}@{host}", update_interval=None)
        self.client = KClient(host, self._handle_message)
        self.client._check_power_status = self.power_is_off
        self.data: dict[str, Any] = {}
        self._paused_flag = False
        self._last_avail = False
        self._power_switch_entity: str | None = (power_switch or "").strip() or None
        self._pending_pause = False
        self._pending_resume = False
        self._last_power_off: bool = self.power_is_off()
        self._config_entry_id: str | None = None  # Will be set after entry is created

    def set_power_switch(self, entity_id: str | None) -> None:
        """Accept updates from options; make it thread-safe to notify."""
        self._power_switch_entity = (entity_id or "").strip() or None
        self._notify_listeners_threadsafe()
        
    def power_is_off(self) -> bool:
        eid = self._power_switch_entity
        if not eid:
            return False
        st = self.hass.states.get(eid)
        if not st:
            _LOGGER.debug("Power switch entity %s not found (assume OFF)", eid)
            return True # FAIL-SAFE: Assume OFF if switch entity isn't ready
        is_off = str(st.state).lower() in ("off", "unavailable", "unknown")
        if is_off:
             _LOGGER.debug("Power switch %s is %s -> skipping connection", eid, st.state)
        return is_off

    async def async_start(self) -> None:
        if self.power_is_off():
            _LOGGER.info("Power switch is OFF; deferring WS connect")
            self._last_power_off = True
            return
        self._last_power_off = False
        await self.client.start()
        
    async def ensure_connected(self) -> bool:
        """Ensure WebSocket connection is active, restart if needed."""
        if self.power_is_off():
            return False
        if not self.client._task or self.client._task.done():
            _LOGGER.info("WebSocket connection lost, restarting...")
            await self.client.start()
            return await self.client.wait_first_connect(timeout=10.0)
        return True
        
    async def async_stop(self) -> None:
        await self.client.stop()
        
    async def wait_first_connect(self, timeout: float = 5.0) -> bool:
        return await self.client.wait_first_connect(timeout=timeout)
    
    async def wait_for_fields(self, fields: Iterable[str], timeout: float = 6.0) -> bool:
        """Wait until all given telemetry fields appear in self.data or timeout.

        Args:
            fields: Iterable of keys expected to be present in telemetry dict.
            timeout: Max seconds to wait.

        Returns:
            True if all fields were observed before timeout, False otherwise.
        """
        try:
            end = self.hass.loop.time() + max(0.0, float(timeout))
            needed = {str(f) for f in fields}
            # Fast path check
            if needed.issubset((self.data or {}).keys()):
                return True
            # Poll lightly; on_message updates self.data frequently when streaming starts
            while self.hass.loop.time() < end:
                if needed.issubset((self.data or {}).keys()):
                    return True
                await asyncio.sleep(0.2)
        except Exception:
            # Never raise from a helper wait; just indicate timeout/False.
            pass
        return False
        
    async def async_handle_power_change(self) -> None:
        """Start/stop WS client when the power switch toggles."""
        now_off = self.power_is_off()
        if now_off and not getattr(self, "_last_power_off", False):
            _LOGGER.info("Power OFF detected; stopping WebSocket client")
            await self.client.stop()
        elif (not now_off) and getattr(self, "_last_power_off", True):
            _LOGGER.info("Power ON detected; starting WebSocket client")
            await self.client.start()
        self._last_power_off = now_off
        self.async_update_listeners()
        
    def _notify_listeners_threadsafe(self) -> None:
        """Always execute listener updates on HA's event loop."""
        # Pass the callable itself (no parens); the loop invokes it safely.
        self.hass.loop.call_soon_threadsafe(self.async_update_listeners)

    def check_stale(self) -> None:
        """Called by periodic timer; may run off the event loop."""
        now_avail = self.available
        if now_avail != getattr(self, "_last_avail", None):
            self._last_avail = now_avail
            self._notify_listeners_threadsafe()

    @property
    def available(self) -> bool:
        return (self.hass.loop.time() - self.client.last_rx_monotonic()) < STALE_AFTER_SECS

    # -------- Pause state management --------
    def mark_paused(self, paused: bool) -> None:
        """Update paused state from telemetry."""
        if self._paused_flag != bool(paused):
            self._paused_flag = bool(paused)
            self.async_update_listeners()

    def paused_flag(self) -> bool:
        return self._paused_flag

    def pending_pause(self) -> bool:
        return bool(self._pending_pause)

    def pending_resume(self) -> bool:
        return bool(self._pending_resume)

    # -------- State helpers --------
    def _is_busy_homing(self) -> bool:
        """Check if printer is homing."""
        return (self.data or {}).get("deviceState") == 7

    def _has_active_job(self) -> bool:
        """Check if a print job is active."""
        d = self.data or {}
        fname = (d.get("printFileName") or "").strip()
        prog = d.get("printProgress", d.get("dProgress"))
        return bool(fname) and prog is not None

    def _is_printing(self) -> bool:
        """Check if printer is actively printing (has job, not paused, not homing)."""
        return self._has_active_job() and not self._paused_flag and not self._is_busy_homing()

    def _recompute_paused_from_telemetry(self) -> None:
        """Update paused state from telemetry data."""
        d = self.data or {}
        st = d.get("state")
        # State 5 is paused; also check explicit pause fields
        telem_paused = (st == 5) or bool(d.get("pause") == 1 or d.get("paused") or d.get("isPaused"))
        self.mark_paused(telem_paused)

    # -------- Queued actions --------
    async def request_pause(self) -> None:
        """Pause now if printable; otherwise queue until printable."""
        if self._is_printing():
            try:
                await self.client.send_set_retry(pause=1)
                _LOGGER.debug("Pause sent immediately")
            except Exception as exc:
                self._pending_pause = True
                _LOGGER.warning("Pause send failed; queued. Error: %s", exc)
        else:
            self._pending_pause = True
            _LOGGER.debug("Pause queued (not in printable state)")

    async def request_resume(self) -> None:
        """Resume now if telemetry shows paused; otherwise queue until paused shows up."""
        if self._paused_flag:
            try:
                await self.client.send_set_retry(pause=0)
                _LOGGER.debug("Resume sent immediately")
            except Exception as exc:
                self._pending_resume = True
                _LOGGER.warning("Resume send failed; queued. Error: %s", exc)
        else:
            self._pending_resume = True
            _LOGGER.debug("Resume queued (not in paused state)")

    async def _flush_pending(self) -> None:
        """Attempt to execute any queued actions when state allows (called on every telemetry frame)."""
        if self._pending_pause and self._is_printing():
            try:
                await self.client.send_set_retry(pause=1)
                self._pending_pause = False
                _LOGGER.debug("Queued pause executed")
            except Exception as exc:
                _LOGGER.warning("Queued pause failed; will retry. Error: %s", exc)

        if self._pending_resume and self._paused_flag:
            try:
                await self.client.send_set_retry(pause=0)
                self._pending_resume = False
                _LOGGER.debug("Queued resume executed")
            except Exception as exc:
                _LOGGER.warning("Queued resume failed; will retry. Error: %s", exc)

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        """Handle incoming WebSocket telemetry data."""
        self.data.update(payload)
        self._recompute_paused_from_telemetry()
        
        # Try queued actions if state allows
        try:
            await self._flush_pending()
        except Exception:
            _LOGGER.exception("flush_pending failed")
        
        self.async_update_listeners()
