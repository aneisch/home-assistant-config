"""Coordinator for Creality 3D printers."""
from __future__ import annotations
import logging
import asyncio
import json
from typing import Any, Iterable
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore[import]
from .ws_client import KClient
from .utils import ModelDetection
from .const import (
    DOMAIN,
    STALE_AFTER_SECS,
    CONF_NOTIFY_DEVICE,
    CONF_NOTIFY_COMPLETED,
    CONF_NOTIFY_ERROR,
    CONF_NOTIFY_MINUTES_TO_END,
    CONF_MINUTES_TO_END_VALUE,
    CONF_POLLING_RATE,
    DEFAULT_POLLING_RATE,
    MR_PORT,
    MR_POLL_INTERVAL,
    MR_POLL_TIMEOUT,
    MR_QUERY_PARAMS,
)

_LOGGER = logging.getLogger(__name__)


class KCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage connection and data for the printer."""
    def __init__(
        self, hass, host: str, power_switch: str | None = None, config_entry_id: str | None = None
    ):
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}@{host}", update_interval=None)
        self.client = KClient(host, self._handle_message)
        self.data: dict[str, Any] = {}
        self._paused_flag = False
        self._last_avail = False
        self._power_switch_entity: str | None = (power_switch or "").strip() or None
        self._pending_pause = False
        self._pending_resume = False
        self._last_power_off: bool = False
        self._config_entry_id: str | None = config_entry_id  # Will be set after entry is created
        
        # Notification & Performance
        self._notify_device = None
        self._notify_completed = False
        self._notify_error = False
        self._notify_minutes_to_end = False
        self._minutes_to_end_value = 5
        self._polling_rate = DEFAULT_POLLING_RATE
        self._last_update_ts = 0.0
        
        # Notification state tracking
        self._last_print_state = None
        self._last_filename = None
        self._notified_completed = False
        self._notified_minutes_to_end = False
        self._last_error_code = 0
        self._last_mr_poll = 0.0
        
        # Extended status tracking
        self._notified_filament_runout = False
        
        # Caches
        self._is_k2_base: bool | None = None

        if self._config_entry_id:
            self._load_options()

        # Only enable power detection if a switch is configured
        if self._power_switch_entity:
            self.client._check_power_status = self.power_is_off
            self._last_power_off = self.power_is_off()
            _LOGGER.debug("Power switch configured: %s (initial state: %s)", 
                         self._power_switch_entity, "OFF" if self._last_power_off else "ON")
        else:
            _LOGGER.debug("No power switch configured; connection will retry continuously")

    def _load_options(self):
        if not self._config_entry_id:
            return
        entry = self.hass.config_entries.async_get_entry(self._config_entry_id)
        if not entry:
            return
            
        options = entry.options
        self._notify_device = options.get(CONF_NOTIFY_DEVICE)
        self._notify_completed = options.get(CONF_NOTIFY_COMPLETED, False)
        self._notify_error = options.get(CONF_NOTIFY_ERROR, False)
        self._notify_minutes_to_end = options.get(CONF_NOTIFY_MINUTES_TO_END, False)
        self._minutes_to_end_value = options.get(CONF_MINUTES_TO_END_VALUE, 5)
        self._polling_rate = options.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
        
        # Pass polling rate to client if relevant, or handle here
        _LOGGER.debug(
            "Loaded options: Polling Rate=%ss, Notify Device=%s",
            self._polling_rate,
            self._notify_device,
        )

    def set_power_switch(self, entity_id: str | None) -> None:
        """Accept updates from options; make it thread-safe to notify."""
        old_entity = self._power_switch_entity
        self._power_switch_entity = (entity_id or "").strip() or None
        
        # Enable or disable power detection based on new config
        if self._power_switch_entity and not old_entity:
            # Power switch was just configured
            # pylint: disable=protected-access
            self.client._check_power_status = self.power_is_off
            self._last_power_off = self.power_is_off()
            _LOGGER.info("Power switch enabled: %s", self._power_switch_entity)
        elif not self._power_switch_entity and old_entity:
            # Power switch was just removed
            # pylint: disable=protected-access
            self.client._check_power_status = None
            self._last_power_off = False
            _LOGGER.info("Power switch disabled; connection will retry continuously")
        
        self._notify_listeners_threadsafe()
        
    def power_is_off(self) -> bool:
        """Check if the power switch is off."""
        # If we are actively connected via WebSocket, trust the connection over the switch state.
        # This allows manual "Reconnect" to work even if the switch entity is lagging or wrong.
        if self.client.is_connected:
            return False

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
        """Start the WebSocket connection."""
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
        # pylint: disable=protected-access
        if not self.client._task or self.client._task.done():
            _LOGGER.info("WebSocket connection lost, restarting...")
            await self.client.start()
            return await self.client.wait_first_connect(timeout=10.0)
        return True
        
    async def async_stop(self) -> None:
        """Stop the WebSocket connection."""
        await self.client.stop()
        
    async def wait_first_connect(self, timeout: float = 5.0) -> bool:
        """Wait for the first successful connection."""
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
        # Only handle power changes if a switch is configured
        if not self._power_switch_entity:
            _LOGGER.debug("Power change handler called but no switch configured; ignoring")
            return
        
        now_off = self.power_is_off()
        was_off = getattr(self, "_last_power_off", False)
        
        if now_off and not was_off:
            _LOGGER.info("Power OFF detected; stopping WebSocket client")
            await self.client.stop()
            self._last_power_off = True
        elif not now_off and was_off:
            _LOGGER.info("Power ON detected; starting WebSocket client")
            # Ensure any stale task is stopped first
            # pylint: disable=protected-access
            if self.client._task and not self.client._task.done():
                _LOGGER.debug("Stopping existing task before restart")
                await self.client.stop()
                # Give it a moment to fully stop
                await asyncio.sleep(0.1)
            await self.client.start()
            self._last_power_off = False
        
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
        # Suppress broken targetBoxTemp:0 from K2 Base port 9999
        if self._is_k2_base is None:
            self._is_k2_base = ModelDetection(payload).is_k2_base
             
        if (payload.get("targetBoxTemp") == 0) and self._is_k2_base:
            payload.pop("targetBoxTemp")

        # Check if boxsInfo is present and we haven't discovered CFS entities yet
        had_cfs = "boxsInfo" in self.data
        self.data.update(payload)
        has_cfs = "boxsInfo" in self.data
        
        if has_cfs and not had_cfs:
            _LOGGER.info("CFS detected in telemetry (first time), triggering dynamic discovery")
            _LOGGER.debug("CFS Raw Data: %s", json.dumps(payload.get("boxsInfo"), default=str))
            async_dispatcher_send(self.hass, f"{DOMAIN}_new_entities_{self._config_entry_id}")
        
        # Log if CFS is connected but we are missing boxsInfo
        if payload.get("cfsConnect") == 1 and not has_cfs:
             # Only log this occasionally or if it's a change to avoid spam? 
             # For now, let's log it if we expected it.
             pass


        self._recompute_paused_from_telemetry()
        
        # Try queued actions if state allows
        try:
            await self._flush_pending()
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("flush_pending failed")

        # --- Notifications ---
        await self._check_notifications(payload)

        # --- Moonraker Fallback (K2 Base) ---
        if self._is_k2_base:
            now = self.hass.loop.time()
            if (now - getattr(self, "_last_mr_poll", 0) > MR_POLL_INTERVAL):
                self._last_mr_poll = now
                self.hass.async_create_task(self._poll_moonraker_extras())
        
        # --- Conditional Throttling (printing only) ---
        # Always update immediately when NOT printing; throttle entity updates only when printing
        now = self.hass.loop.time()
        if self._polling_rate > 0 and self._is_printing():
            if (now - self._last_update_ts) < self._polling_rate:
                return  # Skip listener update to reduce CPU usage while printing
        
        self._last_update_ts = now
        self.async_update_listeners()

    async def _check_notifications(self, _payload: dict[str, Any]):
        """Check logic for sending notifications."""
        if not self._notify_device:
            return

        d = self.data or {}
        fname = d.get("printFileName")
        progress = d.get("printProgress") or d.get("dProgress")
        
        # Check if we started a new print (filename changed)
        # Store last filename in instance to compare
        if getattr(self, "_last_filename", None) != fname:
            self._last_filename = fname
            self._notified_completed = False
            self._notified_minutes_to_end = False
            self._notified_filament_runout = False
            self._last_error_code = 0
        
        if not fname:
            return

        # 1) Completion
        try:
            prog_val = int(progress) if progress is not None else 0
        except (ValueError, TypeError):
            prog_val = 0
            
        if self._notify_completed:
            # If progress is 100% OR state is specific for completion?
            # Using progress >= 100 is most reliable according to sensor logic
            if prog_val >= 100 and not self._notified_completed:
                await self._send_notification(f"Print '{fname}' completed successfully!")
                self._notified_completed = True

        # 2) Error
        if self._notify_error:
            err = d.get("err", {})
            try:
                code = int(err.get("errcode", 0))
            except (ValueError, TypeError):
                code = 0
                
            if code != 0 and code != self._last_error_code:
                key = err.get("key", 0)
                msg = f"Printer Error {code} (Key: {key}) occurred during '{fname}'"
                await self._send_notification(msg)
            
            
            self._last_error_code = code

        # 3) Filament Runout (materialStatus == 1)
        # Using CONF_NOTIFY_ERROR as the toggle since it's an error-like state
        if self._notify_error:
            mat_status = d.get("materialStatus")
            # 1 means runout, 0 means ok (presumably)
            is_runout = False
            try:
                if mat_status is not None and int(mat_status) == 1:
                    is_runout = True
            except (ValueError, TypeError):
                pass

            if is_runout and not self._notified_filament_runout:
                await self._send_notification(f"Filament runout detected during '{fname}'")
                self._notified_filament_runout = True
            elif not is_runout and self._notified_filament_runout:
                # Reset if it goes back to normal (user reloaded filament)
                self._notified_filament_runout = False

        # 4) Minutes to end
        if self._notify_minutes_to_end:
            left_s = d.get("printTimeLeft")
            if left_s is not None:
                try:
                    left_min = float(left_s) / 60.0
                    target_min = self._minutes_to_end_value
                    
                    if 0 < left_min <= target_min and not self._notified_minutes_to_end:
                        await self._send_notification(f"Print '{fname}' finishing in {int(left_min)} minutes.")
                        self._notified_minutes_to_end = True
                    # If time jumps up significantly (e.g. > target + 2m), reset flag?
                    elif left_min > (target_min + 2):
                        self._notified_minutes_to_end = False
                except (TypeError, ValueError):
                    # Invalid printTimeLeft value; skip time-based notification
                    _LOGGER.debug("Invalid printTimeLeft value %r; skipping minutes-to-end notification", left_s)

    async def _send_notification(self, message: str):
        """Send a notification to the configured device."""
        service_data = {"message": message, "title": "Creality Printer"}
        target = self._notify_device
        
        # domain usually "notify" or "mobile_app" (via notify.mobile_app_...)
        # If the user picked an entity from "notify" domain
        # target is the entity ID, e.g. notify.mobile_app_iphone
        
        domain = "notify"
        
        # If entity_id is provided, we might need to parse it
        if target.startswith("notify."):
            service = target.replace("notify.", "")
            # call notify.service_name
            try:
                await self.hass.services.async_call(domain, service, service_data)
            except Exception as e:
                _LOGGER.error("Failed to send notification: %s", e)

    async def _poll_moonraker_extras(self):
        """Poll Moonraker for missing telemetry fields (e.g. chamber target)."""
        # pylint: disable=protected-access
        host = self.client._host
        # Only poll if we have a host and integration is still active
        if not host or self.power_is_off():
            return
            
        url = f"http://{host}:{MR_PORT}/printer/objects/query?{MR_QUERY_PARAMS}"
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, timeout=MR_POLL_TIMEOUT) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    status = res.get("result", {}).get("status", {})
                    fan = status.get("temperature_fan chamber_fan")
                    if fan and "target" in fan:
                        target = fan["target"]
                        # Only update if it's different to avoid unnecessary listener triggers
                        if self.data.get("targetBoxTemp") != target:
                            _LOGGER.debug("Updated targetBoxTemp from Moonraker: %s", target)
                            self.data["targetBoxTemp"] = target
                            self.async_update_listeners()
        except Exception as e:
            # Moonraker might be disabled or port 7125 blocked; fail silently but log debug
            _LOGGER.debug("Failed to poll Moonraker for extras: %s", e)
