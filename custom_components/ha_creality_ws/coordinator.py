"""Coordinator for Creality 3D printers."""
from __future__ import annotations
import logging
import asyncio
import json
import math
import time
from collections.abc import Iterable, Mapping
from typing import Any
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]
from homeassistant.helpers.dispatcher import async_dispatcher_send  # type: ignore[import]
from homeassistant.helpers import entity_registry as er  # type: ignore[import]
from homeassistant.helpers.translation import async_get_translations  # type: ignore[import]
from homeassistant.util import slugify  # type: ignore[import]
from .ws_client import KClient
from .utils import (
    BUSY_PRINT_STATES,
    ModelDetection,
    derive_activity_state,
    safe_float,
)
from .notification_rules import (
    ALERT_ERROR,
    ALERT_RUNOUT,
    EVENT_COMPLETED,
    EVENT_SOON,
    EVENT_STOPPED,
    PHASE_PAUSED,
    PHASE_PRINTING,
    PHASE_START,
    JobEndWatch,
    JobEvent,
    LiveCardState,
    LiveSnapshot,
    NotifyLinks,
    NotifyVisuals,
    PushReason,
    ACTION_DISMISS,
    ACTION_PAUSE,
    ACTION_RESUME,
    ACTION_STOP,
    action_ids,
    build_actions,
    build_alert_payload,
    format_duration,
    format_filament_length,
    build_clear_payload,
    build_event_payload,
    build_live_payload,
    coerce_targets,
    compute_when,
    display_filename,
    is_live_capable,
    is_mobile_target,
    notify_service_slug,
    is_new_job_cycle,
    render_user_template,
    TEMPLATE_FIELDS,
    notify_tag_base,
    stringify_data,
)
from .const import (
    DOMAIN,
    STALE_AFTER_SECS,
    CLEAR_NOTIFICATION_MARKER,
    CONF_NOTIFY_ACTIONS,
    CONF_NOTIFY_CAMERA_SNAPSHOT,
    CONF_NOTIFY_LIVE,
    CONF_NOTIFY_PREVIEW_IMAGE,
    CONF_NOTIFY_TAP_PATH,
    CONF_NOTIFY_COMPLETED,
    CONF_NOTIFY_ERROR,
    CONF_NOTIFY_MINUTES_TO_END,
    CONF_MINUTES_TO_END_VALUE,
    NOTIFY_ONLY_OPTION_KEYS,
    NOTIFY_TEMPLATE_OPTIONS,
    LATE_DISCOVERY_FIELDS,
    GCODE_FILE_RESPONSE,
    GCODE_INFO_KEY,
    GCODE_INFO_MAX_ATTEMPTS,
    GCODE_INFO_RETRY_SECS,
    BUS_EVENT_PRINT_ERROR,
    BUS_EVENT_PRINT_FINISHED,
    BUS_EVENT_PRINT_STARTED,
    BUS_EVENT_PRINT_STOPPED,
    NOTIFY_BODY_SEPARATOR,
    NOTIFY_CHANNEL_KEY_ALERT,
    NOTIFY_CHANNEL_KEY_DONE,
    NOTIFY_CHANNEL_KEY_LIVE,
    NOTIFY_CHANNEL_KEY_SOON,
    NOTIFY_LIVE_STALE_CLEAR_SECS,
    NOTIFY_PRIME_GRACE_SECS,
    PREVIEW_REASONS_UNUSABLE,
    CONF_POLLING_RATE,
    DEFAULT_POLLING_RATE,
    MR_PORT,
    MR_POLL_INTERVAL,
    MR_POLL_TIMEOUT,
    MR_QUERY_PARAMS,
)

_LOGGER = logging.getLogger(__name__)


def _warn_on_unsendable(data: dict[str, Any], target: str) -> None:
    """Complain in our own log if a payload cannot survive the push relay.

    Android delivery is an FCM data message whose values must be strings, and
    a single stray int or bool makes the relay reject the *whole* push. Home
    Assistant catches that failure internally -- it never reaches us, and what
    it logs is a bare "Error sending notification to <device>" with the reason
    only at DEBUG. So the defect is invisible from here by construction, and it
    twice survived a release for exactly that reason.

    This cannot prevent the rejection; it makes it attributable. A grep-able
    line naming the offending keys beats bisecting a payload against a phone,
    which is how both of those bugs were eventually found.
    """
    offenders = [
        key for key, value in data.items() if isinstance(value, (bool, int, float))
    ]
    offenders += [
        f"{key}[{index}].{inner}"
        for key, value in data.items()
        if isinstance(value, (list, tuple))
        for index, entry in enumerate(value)
        if isinstance(entry, dict)
        for inner, inner_value in entry.items()
        if isinstance(inner_value, (bool, int, float))
    ]
    if offenders:
        _LOGGER.warning(
            "Notification payload for %s carries non-string value(s) %s; the "
            "push relay will reject the whole message. This is a bug in the "
            "integration -- please report it",
            target,
            ", ".join(sorted(offenders)),
        )


class KCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage connection and data for the printer."""
    def __init__(self, hass, host: str, power_switch: str | None = None, config_entry=None):
        # config_entry is passed explicitly rather than left to Home Assistant's
        # ContextVar. It resolved to the same entry either way, but only while
        # running inside async_setup_entry -- and `self.config_entry` is what
        # every options and cache read below goes through, so it should not
        # depend on where the coordinator happens to be constructed.
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}@{host}",
            update_interval=None,
            config_entry=config_entry,
        )
        self.client = KClient(host, self._handle_message)
        self.data: dict[str, Any] = {}
        self._paused_flag = False
        self._last_avail = False
        self._power_switch_entity: str | None = (power_switch or "").strip() or None
        self._pending_pause = False
        self._pending_resume = False
        self._last_power_off: bool = False
        
        # Notification & Performance
        self._notify_targets: list[str] = []
        self._notify_live = False
        self._notify_actions = False
        self._notify_preview_image = True
        self._notify_camera_snapshot = True
        self._notify_tap_path = ""
        # Notification name -> the user's own text for it. Empty unless someone
        # filled a field in, and every consumer falls back to the shipped,
        # translated sentence, so the default path is untouched by this.
        self._notify_templates: dict[str, str] = {}
        # The options as of the last `_load_options`; see `notifications_only_change`.
        self._loaded_options: dict[str, Any] | None = None
        # (notification, template) pairs already complained about; see
        # `_custom_message`.
        self._notify_template_warned: set[tuple[str, str]] = set()
        self._live_card = LiveCardState()
        # Watches the running job so a print that is stopped -- from the
        # printer's screen, the Creality app or Home Assistant -- is noticed.
        # See `JobEndWatch`: none of those three announces itself in telemetry.
        self._job_end_watch = JobEndWatch()
        # Notifications retired in state but not yet taken off the phone.
        # Settled at the end of the frame: the card's debt is cancelled if a
        # terminal banner went out to replace it, the reminder's never is,
        # because nothing else shares its tag. Neither is dropped while
        # undeliverable -- it stays owed until there is somewhere to send it.
        self._card_dismiss_owed = False
        self._soon_dismiss_owed = False
        # An error or runout alert is on a phone. Errors and runouts share one
        # tag, so this is deliberately not two flags: whichever condition
        # resolves last is the one that gets to take the alert away.
        self._alert_showing = False
        # Notification text is translated at runtime; None until loaded.
        self._notify_strings: dict[str, str] | None = None
        # (platform, unique suffix) -> entity id. Populated lazily: the
        # platforms are forwarded after this coordinator exists, so nothing
        # can be resolved here.
        self._entity_id_cache: dict[tuple[str, str], str] = {}
        # notify target -> companion `os_name`. Resolved lazily; a target the
        # user has just added would not be in a cache built at setup.
        self._target_os_cache: dict[str, str | None] = {}
        self._notify_completed = False
        self._notify_error = False
        self._notify_minutes_to_end = False
        self._minutes_to_end_value = 5
        self._polling_rate = DEFAULT_POLLING_RATE
        self._last_update_ts = 0.0
        
        # Notification state tracking
        self._last_filename = None
        self._notified_completed = False
        self._notified_minutes_to_end = False
        self._last_error_code = 0
        self._last_mr_poll = 0.0
        # Seconds the current job has been running, as last reported. Only ever
        # goes backwards when the printer starts a new job, which is what tells a
        # reprint of the same file apart from end-of-print progress jitter.
        self._last_job_time: float | None = None

        # Notifications are suppressed until the printer's current state has been
        # captured as a baseline, so a job that already finished before Home
        # Assistant started does not fire a fresh "completed" notification on
        # every restart (issue #112).
        self._notify_primed = False
        self._notify_prime_deadline: float | None = None
        
        # Extended status tracking
        self._notified_filament_runout = False
        self._notified_started = False
        self._notified_stopped = False
        
        # Caches
        self._is_k2_base: bool | None = None

        # Sliced-G-code metadata. `_gcode_info_file` is the file name the cached
        # entry was resolved for, and it is set even when the listing held no
        # match, so a file the printer has no metadata for is asked about once
        # rather than on every frame. `_gcode_info_attempts` only bounds the
        # case where the request draws no reply at all.
        self._gcode_info_file: str | None = None
        self._gcode_info_requested_for: str | None = None
        self._gcode_info_request_ts: float = 0.0
        self._gcode_info_attempts: int = 0

        if self.config_entry:
            self._load_options()

        # Only enable power detection if a switch is configured
        if self._power_switch_entity:
            self.client._check_power_status = self.power_is_off
            self._last_power_off = self.power_is_off()
            _LOGGER.debug("Power switch configured: %s (initial state: %s)", 
                         self._power_switch_entity, "OFF" if self._last_power_off else "ON")
        else:
            _LOGGER.debug("No power switch configured; connection will retry continuously")

    @property
    def entry_id(self) -> str | None:
        """The config entry's id, or None when there is no entry (tests)."""
        return self.config_entry.entry_id if self.config_entry else None

    def _load_options(self):
        if not self.config_entry:
            return
        options = self.config_entry.options
        # A copy, kept so `notifications_only_change` can tell what a later
        # options update actually touched. The entry's own mapping is mutated
        # in place by Home Assistant, so holding a reference would compare the
        # new options against themselves and find nothing changed.
        self._loaded_options = dict(options)
        self._notify_targets = coerce_targets(options)
        self._notify_live = bool(options.get(CONF_NOTIFY_LIVE, False))
        self._notify_actions = bool(options.get(CONF_NOTIFY_ACTIONS, False))
        self._notify_preview_image = bool(options.get(CONF_NOTIFY_PREVIEW_IMAGE, True))
        self._notify_camera_snapshot = bool(options.get(CONF_NOTIFY_CAMERA_SNAPSHOT, True))
        self._notify_tap_path = str(options.get(CONF_NOTIFY_TAP_PATH) or "").strip()
        # Blank and whitespace-only are both "use the shipped text": a user who
        # clears a field must get the default back, and an options dict is
        # never rewritten to drop the key.
        self._notify_templates = {}
        self._notify_template_warned.clear()
        for name, key in NOTIFY_TEMPLATE_OPTIONS.items():
            text = options.get(key)
            if isinstance(text, str) and text.strip():
                self._notify_templates[name] = text.strip()
        # A rename or a disabled entity invalidates these, and an options
        # change is the one moment we know we are being re-read.
        self._entity_id_cache.clear()
        self._target_os_cache.clear()
        self._notify_strings = None
        self._notify_completed = options.get(CONF_NOTIFY_COMPLETED, False)
        self._notify_error = options.get(CONF_NOTIFY_ERROR, False)
        self._notify_minutes_to_end = options.get(CONF_NOTIFY_MINUTES_TO_END, False)
        self._minutes_to_end_value = options.get(CONF_MINUTES_TO_END_VALUE, 5)
        self._polling_rate = options.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
        
        # Pass polling rate to client if relevant, or handle here
        _LOGGER.debug(
            "Loaded options: Polling Rate=%ss, Notify targets=%d",
            self._polling_rate,
            len(self._notify_targets),
        )
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

    def _job_state(self) -> str:
        """What the current job is doing, from the one place the mapping lives.

        There used to be a second definition here -- a job counted as
        "printing" if it merely had a file name and a progress value -- which
        called a finished job (progress >= 100) and a stopped one (state 4)
        printing, and ignored self-test entirely. A pause request at the end of
        a print was therefore sent to a printer that had already stopped.

        Deliberately the *activity* state, not the display state: a non-zero
        `err.errcode` the printer never clears would otherwise report "error"
        for the rest of the print and make the job impossible to pause. The
        status sensor still shows "error" -- that is what a user wants to see;
        it just should not decide whether a pause can be sent.
        """
        return derive_activity_state(
            self.data or {},
            power_off=self.power_is_off(),
            available=self.available,
            paused_flag=self._paused_flag,
        )

    def _recompute_paused_from_telemetry(self) -> None:
        """Update paused state from telemetry data."""
        d = self.data or {}
        st = d.get("state")
        # State 5 is paused; also check explicit pause fields
        telem_paused = (st == 5) or bool(d.get("pause") == 1 or d.get("paused") or d.get("isPaused"))
        self.mark_paused(telem_paused)

    # -------- Queued actions --------
    async def request_pause(self) -> None:
        """Pause now if the printer is printing, or queue it if it is about to be.

        Only queued while the job is still busy. Queuing a pause for a finished,
        stopped or idle printer would leave it armed until the *next* print,
        which would then pause itself the moment it started.
        """
        state = self._job_state()

        if state == "paused":
            _LOGGER.debug("Pause ignored: the printer is already paused")
            return

        # Homing moves are excluded deliberately: the printer is mid-gcode and a
        # pause sent then is at best ignored.
        if state == "printing" and not self._is_busy_homing():
            try:
                await self.client.send_set_retry(pause=1)
                _LOGGER.debug("Pause sent immediately")
            except Exception as exc:  # pylint: disable=broad-except
                self._pending_pause = True
                _LOGGER.warning("Pause send failed; queued. Error: %s", exc)
            return

        if state in BUSY_PRINT_STATES:
            self._pending_pause = True
            _LOGGER.debug("Pause queued: printer is %s, not printing yet", state)
            return

        _LOGGER.warning("Pause ignored: the printer is %s, not printing", state)

    async def request_resume(self) -> None:
        """Resume now if the printer reports paused, or queue until it does.

        Queued only while the job is busy, for the same reason as the pause
        above: telemetry lags a pause the user just requested, but a resume left
        armed past the end of a job would fire into the next one.
        """
        state = self._job_state()

        if state == "paused":
            try:
                await self.client.send_set_retry(pause=0)
                _LOGGER.debug("Resume sent immediately")
            except Exception as exc:  # pylint: disable=broad-except
                self._pending_resume = True
                _LOGGER.warning("Resume send failed; queued. Error: %s", exc)
            return

        if state in BUSY_PRINT_STATES:
            self._pending_resume = True
            _LOGGER.debug("Resume queued: printer is %s, not paused yet", state)
            return

        _LOGGER.warning("Resume ignored: the printer is %s, not paused", state)

    async def _flush_pending(self, state: str | None = None) -> None:
        """Run any queued pause/resume once the state allows.

        Called on every telemetry frame. `state` is passed in by the frame
        handler so it is derived once rather than per consumer.
        """
        if state is None:
            state = self._job_state()

        # A queued action outlives the job it was meant for otherwise, and would
        # fire as soon as the next print started.
        if (self._pending_pause or self._pending_resume) and state not in BUSY_PRINT_STATES:
            _LOGGER.debug(
                "Dropping queued pause/resume: the printer is %s and the job is over",
                state,
            )
            self._pending_pause = False
            self._pending_resume = False
            return

        if self._pending_pause and state == "printing":
            try:
                await self.client.send_set_retry(pause=1)
                self._pending_pause = False
                _LOGGER.debug("Queued pause executed")
            except Exception as exc:
                _LOGGER.warning("Queued pause failed; will retry. Error: %s", exc)

        if self._pending_resume and state == "paused":
            try:
                await self.client.send_set_retry(pause=0)
                self._pending_resume = False
                _LOGGER.debug("Queued resume executed")
            except Exception as exc:
                _LOGGER.warning("Queued resume failed; will retry. Error: %s", exc)

    def merge_telemetry(self, payload: dict[str, Any]) -> None:
        """Merge telemetry into self.data, firing the discovery signal once.

        Entities gated on a capability field can only be created once the printer
        has actually reported it, which may be long after the platforms were set
        up. The first appearance of any LATE_DISCOVERY_FIELDS entry fires one
        signal so every platform can re-check.

        Every writer of a gating field has to come through here. Writing straight
        into self.data both skips the signal and consumes the one-shot, because
        the field is then no longer "newly seen" when a later frame carries it --
        which is what made the chamber control unreachable on a K2 Base, whose
        targetBoxTemp only ever arrives via the Moonraker fallback.
        """
        newly_seen = [f for f in LATE_DISCOVERY_FIELDS if f not in self.data and f in payload]

        self.data.update(payload)

        if newly_seen:
            _LOGGER.info(
                "Telemetry reported %s for the first time; triggering dynamic discovery",
                ", ".join(newly_seen),
            )
            if "boxsInfo" in newly_seen:
                _LOGGER.debug("CFS Raw Data: %s", json.dumps(payload.get("boxsInfo"), default=str))
            async_dispatcher_send(self.hass, f"{DOMAIN}_new_entities_{self.entry_id}")

    @staticmethod
    def _match_gcode_entry(
        entries: list[Any], filename: str
    ) -> dict[str, Any] | None:
        """Find the listing entry describing `filename`.

        `printFileName` is a full path on every printer seen so far, and entries
        carry both `path` and a bare `name`, so the path is the exact match. The
        name is kept as a fallback for firmware that reports the running job by
        base name alone, where the path comparison could never hit.
        """
        base = filename.rsplit("/", 1)[-1]
        fallback: dict[str, Any] | None = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("path") == filename:
                return entry
            if fallback is None and entry.get("name") == base:
                fallback = entry
        return fallback

    def _invalidate_gcode_info(self) -> None:
        """Drop metadata that belongs to a job which is no longer the current one.

        Written straight into self.data rather than through merge_telemetry, and
        only when the key is already present: the entities are gated on this
        key's first appearance, and both deleting it and seeding it with None
        would spend that one-shot on a job whose metadata never arrived.
        """
        if self.data.get(GCODE_INFO_KEY) is not None:
            self.data[GCODE_INFO_KEY] = None

    def _absorb_gcode_file_listing(self, payload: dict[str, Any]) -> None:
        """Reduce a G-code metadata listing to the entry for the running job.

        The listing describes every file on the printer and is removed from the
        payload here, before merge_telemetry would put all of it into
        coordinator data -- which templates, the dashboard card and the
        notification payloads all read.
        """
        if GCODE_FILE_RESPONSE not in payload:
            return

        entries = payload.pop(GCODE_FILE_RESPONSE)
        filename = payload.get("printFileName") or self.data.get("printFileName")
        if not filename:
            return
        if not isinstance(entries, list):
            _LOGGER.debug(
                "Ignoring %s: expected a list, got %s",
                GCODE_FILE_RESPONSE,
                type(entries).__name__,
            )
            return

        entry = self._match_gcode_entry(entries, filename)
        # Recorded either way. A file the printer lists no metadata for is a
        # settled answer, not a reason to keep asking.
        self._gcode_info_file = filename
        self._gcode_info_attempts = 0

        if entry is None:
            self._invalidate_gcode_info()
            _LOGGER.debug(
                "No sliced metadata for %s among %d listed files", filename, len(entries)
            )
            return

        self.merge_telemetry({GCODE_INFO_KEY: entry})

    async def _maybe_request_gcode_info(self) -> None:
        """Ask for the metadata listing when the running file has changed."""
        filename = self.data.get("printFileName")
        if not filename or filename == self._gcode_info_file:
            return

        if filename != self._gcode_info_requested_for:
            self._gcode_info_requested_for = filename
            self._gcode_info_attempts = 0
            self._invalidate_gcode_info()
        elif self._gcode_info_attempts >= GCODE_INFO_MAX_ATTEMPTS:
            # Firmware that does not implement the request answers nothing at
            # all, so silence is the only signal there is to give up on.
            return
        elif (self.hass.loop.time() - self._gcode_info_request_ts) < GCODE_INFO_RETRY_SECS:
            return

        self._gcode_info_attempts += 1
        self._gcode_info_request_ts = self.hass.loop.time()
        try:
            await self.client.request_gcode_file_info()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("Sliced-metadata request failed for %s: %s", filename, exc)

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        """Handle incoming WebSocket telemetry data."""
        # Suppress broken targetBoxTemp:0 from K2 Base port 9999.
        # Only decide once a frame actually identifies the printer: the board code
        # lives in model/modelVersion, which arrive across several frames (see the
        # wait_for_fields call in async_setup_entry). Latching False off a first
        # frame that carried neither left a real K2 Base without the suppression
        # and without the Moonraker poll -- the only source of its targetBoxTemp --
        # so the chamber target snapped back to 0 after every set.
        if self._is_k2_base is None and (
            payload.get("model") or payload.get("modelVersion")
        ):
            self._is_k2_base = ModelDetection(payload).is_k2_base
             
        if (payload.get("targetBoxTemp") == 0) and self._is_k2_base:
            payload.pop("targetBoxTemp")

        self._absorb_gcode_file_listing(payload)

        self.merge_telemetry(payload)

        self._recompute_paused_from_telemetry()
        
        # Derived once per frame and handed to both consumers below.
        job_state = self._job_state()

        # Try queued actions if state allows
        try:
            await self._flush_pending(job_state)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("flush_pending failed")

        # --- Notifications ---
        await self._check_notifications(payload)

        # --- Sliced G-code metadata ---
        # Must stay above the throttle below, which returns early while printing
        # and would otherwise swallow the one frame that changed the file name.
        await self._maybe_request_gcode_info()

        # --- Moonraker Fallback (K2 Base) ---
        if self._is_k2_base:
            now = self.hass.loop.time()
            if (now - getattr(self, "_last_mr_poll", 0) > MR_POLL_INTERVAL):
                self._last_mr_poll = now
                self.hass.async_create_task(self._poll_moonraker_extras())
        
        # --- Conditional Throttling (printing only) ---
        # Always update immediately when NOT printing; throttle entity updates only when printing
        now = self.hass.loop.time()
        if self._polling_rate > 0 and job_state in BUSY_PRINT_STATES:
            if (now - self._last_update_ts) < self._polling_rate:
                return  # Skip listener update to reduce CPU usage while printing
        
        self._last_update_ts = now
        self.async_update_listeners()

    @staticmethod
    def _print_seconds_left(d: dict[str, Any]) -> float | None:
        """Seconds remaining in the current print, or None.

        The printer streams this as `printLeftTime`; `printTimeLeft` is only kept
        as a fallback because the notification code used to look for that name
        exclusively, which meant the minutes-to-end notification never fired.
        """
        for key in ("printLeftTime", "printTimeLeft"):
            value = safe_float(d.get(key))
            if value is not None:
                return value
        return None

    def _prime_notification_state(self, d: dict[str, Any]) -> None:
        """Record the printer's state at startup without notifying about it.

        The printer keeps reporting the last job's file name and 100% progress
        long after it finished, so a freshly started coordinator would treat that
        stale state as a brand new completion (issue #112). Marking the
        already-true conditions as "already notified" makes the first real
        transition the first notification.
        """
        self._notify_primed = True
        self._last_filename = d.get("printFileName")

        # Same explicit None check as _check_notifications: `or` would baseline a
        # genuine 0% frame off a stale dProgress of 100 and mark the job already
        # complete. The re-arm clears that a frame later, but the two paths must
        # not disagree about the same telemetry.
        progress = d.get("printProgress")
        if progress is None:
            progress = d.get("dProgress")
        try:
            prog_val = int(progress) if progress is not None else 0
        except (ValueError, TypeError):
            prog_val = 0
        self._notified_completed = prog_val >= 100

        try:
            self._last_error_code = int((d.get("err") or {}).get("errcode", 0))
        except (AttributeError, ValueError, TypeError):
            self._last_error_code = 0

        try:
            self._notified_filament_runout = int(d.get("materialStatus") or 0) == 1
        except (ValueError, TypeError):
            self._notified_filament_runout = False

        left_s = self._print_seconds_left(d)
        self._notified_minutes_to_end = bool(
            left_s is not None and 0 < (left_s / 60.0) <= self._minutes_to_end_value
        )

        self._last_job_time = safe_float(d.get("printJobTime"))

        # Adopting a job that was already running is not the same event as one
        # beginning, so the started latch is closed rather than armed. Same
        # for a job the printer is still reporting as stopped.
        self._notified_started = True
        primed_state = derive_activity_state(
            d,
            power_off=self.power_is_off(),
            available=self.available,
            paused_flag=self._paused_flag,
        )
        self._notified_stopped = primed_state == "stopped"

        # The card is baselined too, or a restart would push a live activity for
        # a print that finished last week -- issue #112 reincarnated as a push.
        # Milestone comes off the progress we can actually see so the first real
        # push is a start, not a redundant milestone.
        self._live_card.reset_for_new_job(progress=prog_val)

        # A card outlives the process. `card_active` is in-memory, so after a
        # restart nothing knows one is still on a phone -- and `notifier_tick`
        # only acts on a card it believes exists, so it will not tidy up either.
        # A print that finished while Home Assistant was down therefore left a
        # card reading "42%" that nothing would ever remove.
        #
        # Only when no resync is coming: if the printer is mid-job the START
        # push below replaces the card in place, and dismissing it first would
        # flicker and spend an iOS push-to-start slot for nothing.
        if self._notify_live and primed_state not in BUSY_PRINT_STATES:
            self._notify_dispatch(
                build_clear_payload(f"{self._notify_tag_base()}_live"),
                kind="live:clear:adopt",
                live_only=True,
            )

        _LOGGER.debug(
            "Notification baseline captured: file=%s progress=%s completed=%s "
            "err=%s runout=%s near_end=%s",
            self._last_filename,
            prog_val,
            self._notified_completed,
            self._last_error_code,
            self._notified_filament_runout,
            self._notified_minutes_to_end,
        )

    async def _check_notifications(self, _payload: dict[str, Any]) -> None:
        """Check logic for sending notifications."""
        d = self.data or {}
        fname = d.get("printFileName")
        # Explicit None check, matching derive_print_state: `or` would treat a
        # genuine 0% as missing and fall back to dProgress, which still holds the
        # finished job's 100 on the first frame of a reprint. The completion flag
        # would then never re-arm and the next finish would go unnotified.
        progress = d.get("printProgress")
        if progress is None:
            progress = d.get("dProgress")

        # Baseline the current state before anything can be notified. Telemetry
        # arrives incrementally, so wait for a frame that carries both the file
        # name and the progress, but never longer than the grace window (an idle
        # printer may report neither).
        if not self._notify_primed:
            now = self.hass.loop.time()
            if self._notify_prime_deadline is None:
                self._notify_prime_deadline = now + NOTIFY_PRIME_GRACE_SECS
            if (fname and progress is not None) or now >= self._notify_prime_deadline:
                self._prime_notification_state(d)
            return

        # Not an early return any more. The bus events below are the supported
        # way to build your own notification text, in your own language, and they
        # have to work for someone who configured no notify target at all. Only
        # *delivery* is gated. Keeping the state tracking unconditional also
        # fixes a latent bug: `_last_job_time` used to stop advancing without a
        # target, so enabling notifications mid-print saw a phantom restart.
        deliver = bool(self._notify_targets)
        if deliver:
            await self._async_load_notify_strings()
            # Without text there is nothing to send. The bus events below still
            # fire: they carry structured data, not prose.
            deliver = bool(self._notify_strings)

        try:
            prog_val = int(progress) if progress is not None else 0
        except (ValueError, TypeError):
            prog_val = 0

        # `printJobTime` counts up for as long as one job runs, so it only ever
        # goes backwards when the printer starts another one. That is the one
        # unambiguous new-cycle signal in this telemetry: the file name stays the
        # same on a reprint, and progress dips below 100 for reasons that have
        # nothing to do with a new job (see the completion re-arm below).
        job_time = safe_float(d.get("printJobTime"))
        job_restarted = (
            job_time is not None
            and self._last_job_time is not None
            and job_time < self._last_job_time
        )
        if job_time is not None:
            self._last_job_time = job_time

        # 0) Has the job we were watching stopped running?
        #
        # Before everything below, because both of the things that reveal a stop
        # also destroy the evidence for it: a cleared file name trips the
        # filename-change reset a few lines down, which dismisses the card and
        # re-arms the latches, and the `if not fname` return after it means this
        # frame is the only chance to say anything at all.
        #
        # Skipped once the completion has been announced. A finished print is
        # the completion branch's business, and this printer resets the progress
        # to 0 a while after a job ends -- which the watch would otherwise read
        # as a print that stopped at 99%.
        state = self._job_state()
        if fname and getattr(self, "_last_filename", None) != fname:
            # A different file is a different job, so the watch forgets the one
            # it was following -- before this frame is folded in, or the reset
            # would throw away the very observation that armed it.
            #
            # Only when there *is* a new name: a name the printer has cleared is
            # the job being watched going away, and the watch's memory of it is
            # the only thing that can still say what stopped and how far it got.
            self._job_end_watch.reset()
        if self._notified_completed:
            self._job_end_watch.reset()
            job_event = None
        else:
            job_event = self._job_end_watch.observe(
                state=state,
                progress=prog_val,
                filename=display_filename(fname) or (fname or ""),
                now_mono=self.hass.loop.time(),
            )

        if job_event is JobEvent.RESTARTED:
            # A job printing again after one ended: re-arm everything that is
            # once per print. The file name has not necessarily changed (the
            # same file reprinted) and the job clock does not go backwards after
            # a stop, so neither of the two older signals catches this.
            _LOGGER.debug("A print is running again; re-arming the job latches")
            self._reset_for_new_job(prog_val)
        elif job_event is JobEvent.ENDED_EARLY and not self._notified_stopped:
            await self._announce_early_end(deliver=deliver)

        # Check if we started a new print (filename changed)
        # Store last filename in instance to compare
        if getattr(self, "_last_filename", None) != fname:
            self._last_filename = fname
            self._notified_minutes_to_end = False
            self._notified_filament_runout = False
            self._last_error_code = 0
            # Baseline completion off the progress we can actually see, exactly
            # as _prime_notification_state does. Telemetry arrives incrementally,
            # so the frame that first carries the new file name usually still
            # carries the *previous* job's 100 -- arming here unconditionally
            # fired "completed" the instant a new job started, and then swallowed
            # the real completion.
            self._notified_completed = prog_val >= 100
            self._reset_for_new_job(prog_val)

        if not fname:
            return

        # The K1C reports a full path; the sensor attributes deliberately
        # keep publishing it raw, but a notification body should not.
        job = display_filename(fname) or fname

        # 0) Started. Deliberately not tied to the frame the file name changes
        # on: telemetry arrives incrementally, so that frame usually still holds
        # the previous job's 100%, and firing there would announce a print
        # beginning at 100%. Waiting for real progress means the event lands on
        # the first frame that actually describes the new job.
        if not self._notified_started and prog_val < 100:
            self._notified_started = True
            self._fire_print_event(BUS_EVENT_PRINT_STARTED, d, job)

        # 1) Completion

        # Progress falling back below 100% means a new job cycle started, even if
        # it reprints the same file (in which case the file name never changes and
        # the reset above never fires). Without this the completion notification
        # only ever arrives once per file name.
        #
        # It has to be a real drop, though. The printer rounds progress up to 100
        # a second before the job ends (with minutes still on the clock), reports
        # 99 once more, and only then finishes -- so re-arming on any dip below
        # 100 sent the completion notification twice for every print, once per
        # crossing. A drop that stays within the jitter band is only a new cycle
        # if the job clock restarted too.
        if is_new_job_cycle(
            prog_val,
            job_restarted,
            ended_at_completion=self._notified_completed,
            ended_early=self._notified_stopped,
        ):
            _LOGGER.debug("Progress back at %s%%; re-arming completion notification", prog_val)
            self._notified_completed = False
            # Same predicate, so the card and the completion notification can
            # never disagree about where one job ends and the next begins.
            self._reset_for_new_job(prog_val)

        # Before the one-shot events below: on the frame a print finishes this
        # ends the activity, and the completion banner then arrives on its own
        # tag rather than landing behind a card that is still counting down.
        if deliver:
            self._update_live_card(self._live_snapshot())

        # Detection below is deliberately *not* wrapped in the per-event
        # option checks -- only the sends are. Three reasons:
        #   * `_notified_completed` is the sole input to is_new_job_cycle(), so
        #     latching it only when completion notifications were enabled meant
        #     a same-file reprint never re-armed: the live card stayed retired
        #     for good and no further start was ever detected.
        #   * `_last_error_code` and the runout latch likewise stopped advancing,
        #     so enabling an option mid-print replayed whatever was already true.
        #   * The bus events are documented to fire regardless of notification
        #     settings; they exist precisely for the user who writes their own
        #     text instead of using ours.
        if prog_val >= 100 and not self._notified_completed:
            if self._notify_completed and deliver:
                await self._notify_event(
                    self._completion_message(d, job), kind=EVENT_COMPLETED
                )
            self._fire_print_event(BUS_EVENT_PRINT_FINISHED, d, job)
            self._notified_completed = True

        # 1b) Stopped or cancelled. Shares the completion toggle: someone who
        # wants to be told a print finished wants to be told when it did not,
        # and a card that simply vanishes explains nothing. Completion wins when
        # both apply, because derive_print_state ranks progress >= 100 above
        # state 4.
        if state == "stopped" and not self._notified_stopped:
            if self._notify_completed and deliver:
                await self._notify_event(
                    self._custom_message("stopped")
                    or self._t(
                        "stopped", device=self._notify_title(), progress=prog_val
                    ),
                    kind=EVENT_STOPPED,
                )
            self._fire_print_event(BUS_EVENT_PRINT_STOPPED, d, job)
            self._notified_stopped = True

        # 2) Error
        code = self._error_code(d)
        if code != 0 and code != self._last_error_code:
            key = (d.get("err") or {}).get("key", 0)
            if self._notify_error and deliver:
                await self._notify_event(
                    self._custom_message("error", error_key=key)
                    or self._t(
                        "error", device=self._notify_title(), code=code, key=key
                    ),
                    kind=ALERT_ERROR,
                )
            self._fire_print_event(BUS_EVENT_PRINT_ERROR, d, job)
        self._last_error_code = code

        # 3) Filament runout (materialStatus == 1). Shares the error toggle,
        # being an error-like state the user wants to hear about together.
        try:
            mat_status = d.get("materialStatus")
            is_runout = mat_status is not None and int(mat_status) == 1
        except (ValueError, TypeError):
            is_runout = False

        if is_runout and not self._notified_filament_runout:
            if self._notify_error and deliver:
                await self._notify_event(
                    self._custom_message("filament_runout")
                    or self._t(
                        "filament_runout",
                        device=self._notify_title(),
                        state=self._job_state(),
                    ),
                    kind=ALERT_RUNOUT,
                )
            self._notified_filament_runout = True
        elif not is_runout and self._notified_filament_runout:
            # Reset once the user has reloaded.
            self._notified_filament_runout = False

        # 3b) Both conditions clear again: take the alert off the phone. The
        # printer recovering is exactly when a lock screen still reading
        # "filament runout" becomes actively misleading -- and because the two
        # share a tag, this waits for *both*, or resolving one would dismiss
        # the other's alert.
        if self._alert_showing and code == 0 and not is_runout:
            self._alert_showing = False
            if deliver:
                self._notify_dispatch(
                    build_clear_payload(f"{self._notify_tag_base()}_alert"),
                    kind="alert:clear",
                    mobile_only=True,
                )

        # 4) Minutes to end
        # Nothing to compare against until the printer reports a remaining time.
        left_s = self._print_seconds_left(d)
        if left_s is not None:
            left_min = left_s / 60.0
            target_min = self._minutes_to_end_value

            if 0 < left_min <= target_min and not self._notified_minutes_to_end:
                if self._notify_minutes_to_end and deliver:
                    await self._notify_event(
                        self._custom_message(
                            "finishing_soon", minutes=int(left_min)
                        )
                        or self._t(
                            "finishing_soon",
                            device=self._notify_title(),
                            minutes=int(left_min),
                        ),
                        kind=EVENT_SOON,
                    )
                self._notified_minutes_to_end = True
            elif left_min > (target_min + 2):
                # The estimate jumped back up by more than the slack; re-arm.
                self._notified_minutes_to_end = False

        # 5) Settle any dismissal still owed. Every terminal banner above
        # cancels the debt, because it lands on the card's tag and replaces it.
        # Anything left here means the card was retired with nothing to take its
        # place, and the sentinel is the only thing that will.
        # Left owed rather than dropped when there is nowhere to deliver it: a
        # target configured later still has a card to take away.
        if deliver and self._card_dismiss_owed:
            self._card_dismiss_owed = False
            self._clear_live_card(finished=self._live_card.job_finished)
        if deliver and self._soon_dismiss_owed:
            self._soon_dismiss_owed = False
            self._notify_dispatch(
                build_clear_payload(f"{self._notify_tag_base()}_soon"),
                kind="soon:clear",
                mobile_only=True,
            )

    async def _announce_early_end(self, *, deliver: bool) -> None:
        """Say that a print ended before it finished, and tidy up after it.

        Reached from the transition watch rather than from a state word, so the
        frame this runs on has already lost the two things the message needs --
        the file name may be cleared and the progress reset to 0. Both come from
        the watch, which remembers them from the last frame that showed the job
        running. "Stopped at 0%" was what the printer's own telemetry would have
        said.

        The card is retired here rather than left to `_update_live_card`: after
        a stop the printer sits in a state this integration counts as busy
        (state 0 with the file still named), so a card left un-finished would be
        stood straight back up at 0% by the very next frame.
        """
        watch = self._job_end_watch
        job = watch.job_name or display_filename(self._last_filename) or ""
        progress = max(watch.progress, 0)
        _LOGGER.info(
            "Print %s ended at %s%% without finishing; announcing it", job, progress
        )

        # A banner is posted on the card's own tag and replaces it, so the card
        # is retired *silently* when one is coming. When none is -- the user
        # does not want end notifications, or has no target -- this is the only
        # thing that will take it off the phone.
        banner = self._notify_completed and deliver
        if self._live_card.card_active:
            self._clear_live_card(finished=True, send=not banner)
        else:
            self._live_card.finish()
        self._card_dismiss_owed = False

        if banner:
            await self._notify_event(
                self._custom_message("stopped", filename=job, progress=progress)
                or self._t(
                    "stopped", device=self._notify_title(), progress=progress
                ),
                kind=EVENT_STOPPED,
            )

        # The finishing-soon reminder has its own tag, so no banner supersedes
        # it. A print stopped in its last minutes would otherwise leave
        # "finishing in 5 minutes" sitting on the phone for good, and this frame
        # can be the last one that carries a job at all.
        if deliver and (self._notified_minutes_to_end or self._soon_dismiss_owed):
            self._notify_dispatch(
                build_clear_payload(f"{self._notify_tag_base()}_soon"),
                kind="soon:clear",
                mobile_only=True,
            )
        self._soon_dismiss_owed = False

        self._fire_print_event(
            BUS_EVENT_PRINT_STOPPED, self.data or {}, job, progress=progress
        )
        self._notified_stopped = True

    def _reset_for_new_job(self, prog_val: int) -> None:
        """Re-arm the per-job notification latches for a new job.

        The order matters: any card still on a phone is dismissed *before* the
        latch that tracks it is cleared. Resetting first would drop
        `card_active`, leaving nothing that knows a Live Activity is still up --
        and `notifier_tick` would not clean it up either, because it only acts on
        a card it believes exists.
        """
        if self._live_card.card_active:
            self._clear_live_card()
        self._live_card.reset_for_new_job(progress=prog_val)
        self._notified_started = False
        self._notified_stopped = False
        # Also once per print: a job stopped near the end latches this, and the
        # latch only used to clear on a *file name* change -- so reprinting the
        # same file got no reminder. The filename-change caller resets it a few
        # lines later anyway, so this is only ever new information for the other
        # two callers.
        self._notified_minutes_to_end = False

    def _resolve_entity_id(self, platform: str, unique_suffix: str) -> str | None:
        """Entity id of one of our own entities, via the unique id we minted.

        Not derivable from the host: `KEntity` sets `_attr_has_entity_name`, and
        users rename things, so the object id is whatever the registry says.
        Cached, but only once it resolves -- a miss stays a miss so a lookup made
        before the platform finished setting up does not stick forever.

        Registry hits include *disabled* entities, which would 404 on the proxy
        URLs, hence the state check at the call sites.
        """
        key = (platform, unique_suffix)
        cached = self._entity_id_cache.get(key)
        if cached:
            return cached
        try:
            registry = er.async_get(self.hass)
            entity_id = registry.async_get_entity_id(
                platform, DOMAIN, f"{self.client._host}-{unique_suffix}"
            )
        except Exception:  # pylint: disable=broad-except
            return None
        if entity_id:
            self._entity_id_cache[key] = entity_id
        return entity_id

    def _live_entity_state(self, platform: str, unique_suffix: str):
        """The live state of one of our entities, or None if it cannot serve."""
        entity_id = self._resolve_entity_id(platform, unique_suffix)
        if not entity_id:
            return None, None
        state = self.hass.states.get(entity_id)
        if state is None:
            # Registered but disabled or not yet added; the proxy would 404.
            return None, None
        return entity_id, state

    def _notify_media(self, *, include_snapshot: bool) -> NotifyVisuals:
        """Media URLs for a notification, gated on being real pictures.

        Both are relative `/api/...` paths; the companion app fetches them with
        its own credentials, so no token or signed path is involved. Neither is
        attached speculatively: the image entity serves a 1x1 transparent PNG
        when it has no preview, and a camera that cannot snapshot serves a 1x1
        white JPEG. Android renders either as an empty grey box.

        `preview_reason` is only set once something has actually asked the image
        entity for bytes, and Home Assistant does not do that on its own -- so
        an unset value means "not tried yet", not "no good". Excluding only the
        two known-bad reasons lets the first notification of a print carry the
        preview (the companion app's own fetch is what populates it) instead of
        waiting for a dashboard to render the entity first.
        """
        preview_url = None
        if self._notify_preview_image:
            entity_id, state = self._live_entity_state("image", "current_print_preview")
            reason = (getattr(state, "attributes", None) or {}).get("preview_reason")
            if state is not None and reason not in PREVIEW_REASONS_UNUSABLE:
                preview_url = f"/api/image_proxy/{entity_id}"

        snapshot_url = None
        if include_snapshot and self._notify_camera_snapshot:
            entity_id, state = self._live_entity_state("camera", "camera")
            if state is not None and (
                getattr(state, "attributes", None) or {}
            ).get("snapshot_supported"):
                snapshot_url = f"/api/camera_proxy/{entity_id}"

        return NotifyVisuals(preview_url=preview_url, snapshot_url=snapshot_url)

    def _notify_links(self) -> NotifyLinks:
        """Tap targets, sent as both dialects at once.

        A configured dashboard path wins on both platforms. Failing that Android
        gets `entityId:` for the camera, which opens the more-info dialog and its
        live feed with no configuration at all -- but iOS does not support that
        form, so it gets nothing rather than a broken link.
        """
        path = (self._notify_tap_path or "").strip()
        if path.startswith("/"):
            return NotifyLinks(click_action=path, tap_path=path)

        camera_id = self._resolve_entity_id("camera", "camera")
        if camera_id:
            return NotifyLinks(click_action=f"entityId:{camera_id}")

        # No camera configured for this printer: the preview at least shows what
        # is being printed.
        preview_id = self._resolve_entity_id("image", "current_print_preview")
        if preview_id:
            return NotifyLinks(click_action=f"entityId:{preview_id}")

        return NotifyLinks()

    def _live_snapshot(self) -> LiveSnapshot:
        """The subset of telemetry the live card reacts to."""
        d = self.data or {}
        activity_state = derive_activity_state(
            d,
            power_off=self.power_is_off(),
            available=self.available,
            paused_flag=self._paused_flag,
        )
        return LiveSnapshot(
            activity_state=activity_state,
            job_active=activity_state in BUSY_PRINT_STATES,
            progress=self._notify_progress(),
            filename=display_filename(d.get("printFileName")),
            layer=self._int_or_none(d.get("layer")),
            total_layers=self._int_or_none(d.get("TotalLayer")),
            seconds_left=self._print_seconds_left(d),
        )

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        """A whole number from telemetry, or None when there is not one.

        `safe_float` passes nan and inf through, and `int()` raises ValueError on
        the first and OverflowError on the second. Raising here aborts
        `_live_snapshot`, `_check_notifications` and the listener update for the
        whole frame, and `ws_client` only logs "K on_message failed" -- so a
        single malformed value silently costs a frame. Same rule as
        `derive_print_state`, so the two paths agree.
        """
        number = safe_float(value)
        if number is None or not math.isfinite(number):
            return None
        return int(number)

    def _live_message(self, snap: LiveSnapshot) -> str:
        """The card body. Every segment is dropped when its source is unknown.

        Progress, layer and remaining time, and deliberately not the file name:
        the card's title is the printer, iOS gets the job name as the activity's
        subtitle, and a long `.gcode` name pushed the numbers off the end of an
        Android status bar. The numbers are what the card is read for.

        The remaining time is spelled out even while the chronometer is
        counting down to the same moment. The two do not disagree -- both come
        from the same `when` -- and the text is the only one of them a
        notification history, a watch face or a lock screen preview shows.
        """
        custom = self._custom_message("live")
        if custom:
            return custom

        parts: list[str] = []
        if snap.activity_state == "paused":
            parts.append(
                self._t("body_paused", progress=snap.progress)
                if snap.progress is not None
                else self._t("body_paused_unknown")
            )
        elif snap.progress is not None:
            parts.append(self._t("body_progress", progress=snap.progress))
        if snap.layer is not None and snap.total_layers:
            parts.append(
                self._t(
                    "body_layer", layer=snap.layer, total_layers=snap.total_layers
                )
            )
        remaining = format_duration(snap.seconds_left, self._notify_strings or {})
        if remaining:
            parts.append(self._t("body_time_left", duration=remaining))
        return NOTIFY_BODY_SEPARATOR.join(p for p in parts if p) or self._t(
            "body_fallback"
        )

    def _update_live_card(self, snap: LiveSnapshot) -> None:
        """Start, update or end the live print card.

        Runs on every WebSocket frame, so the cheap checks come first and no
        payload is built on a frame that decides to stay quiet.
        """
        if not self._notify_live:
            return

        if self._job_end_watch.pending():
            # The job may have just been stopped, and this printer reports a
            # stopped job as state 0 with the progress reset -- which is still
            # "busy" below, so without this the card's last word on a cancelled
            # print was an immediate refresh reading 0% and "0s left". Nothing
            # is retired either: if the end is confirmed the banner replaces the
            # card in place, and if the frame was only a blip the next one
            # refreshes it with real values.
            return

        if not snap.job_active:
            if self._live_card.card_active:
                # Only reaching 100% retires the card *here*. The jitter this
                # latch defends against happens there and nowhere else, whereas
                # one transient "idle"/"off" frame has to leave the card able to
                # come back.
                #
                # A print that was stopped is retired too, but by
                # `_announce_early_end`, which has decided it really did end and
                # has a banner to put in its place. That is also the only thing
                # that re-arms it: reaching this line with `finished=True` for a
                # stopped job used to mean the same file could never show a card
                # again, because nothing knew a new print had begun.
                finished = snap.progress is not None and snap.progress >= 100
                # Retire the state but send nothing yet. A terminal banner is
                # usually posted on this same tag moments later and replaces the
                # card in place, so dismissing here would only make it flicker.
                #
                # "Usually" is why this is a debt rather than a prediction: it
                # used to key off the *option*, but the banner is also gated on
                # its own one-shot latch. A job whose completion had already
                # been announced -- the printer reports 100% forever, so any
                # restart re-latches it -- produced neither a banner nor a
                # dismissal, and the card sat on the phone for good.
                self._card_dismiss_owed = True
                # The reminder is on its own tag, so no banner will ever
                # supersede it and it always needs taking away by hand.
                self._soon_dismiss_owed = self._notified_minutes_to_end
                self._clear_live_card(finished=finished, send=False)
            return

        now_mono = self.hass.loop.time()
        now_epoch = time.time()
        reason = self._live_card.decide(
            snap=snap, now_mono=now_mono, now_epoch=now_epoch
        )
        if reason is None:
            return

        # Past Apple's eight-hour ceiling the activity is gone, so the live-only
        # keys are dropped and the card degrades to a plain tagged notification
        # that still replaces itself in place.
        expired = self._live_card.is_expired(now_epoch)
        paused = snap.activity_state == "paused"
        when = None if paused else compute_when(now_epoch, snap.seconds_left)
        phase = (
            PHASE_PAUSED
            if paused
            else PHASE_START
            if reason is PushReason.START
            else PHASE_PRINTING
        )
        tag_base = self._notify_tag_base()

        payload = build_live_payload(
            tag=f"{tag_base}_live",
            title=self._notify_title(),
            message=self._live_message(snap),
            phase=phase,
            progress=snap.progress,
            when=when,
            channel=self._t(NOTIFY_CHANNEL_KEY_LIVE),
            status_text=self._live_status_text(phase, paused),
            live_update=not expired,
            group=tag_base,
            # No snapshot: Android re-downloads a big picture on every push and
            # an iOS Live Activity has no image slot for it.
            visuals=self._notify_media(include_snapshot=False),
            links=self._notify_links(),
            actions=self._notify_card_actions(snap),
            # A card is already on the phone, so this push updates one rather
            # than starting one -- which is what makes it silent on iOS.
            refresh=self._live_card.card_active,
            # For the iOS Live Activity's own rendered state.
            job_name=display_filename(snap.filename) or snap.filename or "",
            device_name=self._notify_title(),
        )
        self._notify_dispatch(
            payload, kind=f"live:{reason.value}", live_only=True
        )
        self._live_card.record_push(
            reason=reason,
            snap=snap,
            now_mono=now_mono,
            now_epoch=now_epoch,
            when=when,
        )

    def _live_status_text(self, phase: str, paused: bool) -> str:
        """The short label shown when there is no chronometer to show instead."""
        if paused:
            return self._t("status_paused")
        if phase == PHASE_START:
            return self._t("status_starting")
        return self._t("status_finishing")

    def _clear_live_card(self, *, finished: bool = False, send: bool = True) -> None:
        """End the live activity.

        A same-tag banner does not end one, so this sentinel is the only way to
        dismiss a card that no notification will replace.

        `send=False` retires the state without dismissing anything, for the one
        case where a terminal banner is about to be posted on the same tag: it
        replaces the card by tag identity, and clearing first would dismiss and
        immediately re-create it, which the user sees as a flicker.

        Deliberately not called on unload: `options_update_listener` reloads the
        entry on *any* options change, and clearing there would dismiss and
        re-create the card every time the user toggles something unrelated.
        """
        if send:
            self._notify_dispatch(
                build_clear_payload(f"{self._notify_tag_base()}_live"),
                kind="live:clear",
                live_only=True,
            )
        if finished:
            self._live_card.finish()
        else:
            self._live_card.clear()

    def _fire_print_event(
        self, event: str, d: dict[str, Any], job: str, *, progress: Any = None
    ) -> None:
        """Fire a language-neutral bus event describing the job.

        Deliberately independent of whether any notify target is configured:
        this is what a multi-language household uses to write its own
        notification text in an automation, since a body composed here can only
        ever follow the server's language.

        `progress` overrides what the frame says, for the one event whose frame
        no longer describes the job it is about: a stopped print is revealed by
        telemetry that has already reset the progress to 0, and an automation
        reading this event needs the same number the notification quotes.
        """
        try:
            self.hass.bus.async_fire(
                event,
                {
                    "entry_id": self.entry_id,
                    "host": self.client._host,
                    "device_name": self._notify_title(),
                    "filename": job,
                    "progress": (
                        self._notify_progress() if progress is None else progress
                    ),
                    "layer": self._int_or_none(d.get("layer")),
                    "total_layers": self._int_or_none(d.get("TotalLayer")),
                    "left_seconds": self._print_seconds_left(d),
                    "err_code": self._error_code(d),
                },
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to fire %s", event)

    @staticmethod
    def _error_code(d: dict[str, Any]) -> int:
        try:
            return int((d.get("err") or {}).get("errcode", 0))
        except (AttributeError, ValueError, TypeError):
            return 0

    def _notify_action_ids(self) -> dict[str, str]:
        """Action ids for this printer, namespaced by config entry."""
        return action_ids(self.entry_id or self.client._host)

    def _notify_card_actions(self, snap: LiveSnapshot) -> list[dict[str, Any]] | None:
        """Buttons for the live card.

        Never None. The printer controls are opt-in, but a swipe only clears
        the notification on screen and the next refresh re-posts it under the
        same tag -- which means Dismiss has to be there whatever the user chose,
        or the card could not be retired for the rest of the print.
        """
        return build_actions(
            paused=snap.activity_state == "paused",
            ids=self._notify_action_ids(),
            labels={
                ACTION_PAUSE: self._t("action_pause"),
                ACTION_RESUME: self._t("action_resume"),
                ACTION_STOP: self._t("action_stop"),
                ACTION_DISMISS: self._t("action_dismiss"),
            },
            controls=self._notify_actions,
        )

    async def async_handle_notification_action(self, action: str) -> bool:
        """Run a live-card button. Returns whether the action was ours.

        The exact id match is the only guard needed against two printers
        cross-firing, because the ids are namespaced per config entry.

        Nothing is done to the card afterwards: the next telemetry frame moves
        the state and re-renders it, matching how the pause/resume buttons
        already behave rather than guessing optimistically.
        """
        ids = self._notify_action_ids()
        if action == ids[ACTION_PAUSE]:
            await self.request_pause()
        elif action == ids[ACTION_RESUME]:
            await self.request_resume()
        elif action == ids[ACTION_STOP]:
            await self.async_stop_print()
        elif action == ids[ACTION_DISMISS]:
            # A swipe only removes the notification that is on screen; the
            # next live-card refresh posts it again under the same tag. This
            # retires the card for the rest of the print instead, which is
            # what a user asking to be rid of it means -- and `finish()`
            # rather than `clear()` so the next frame does not put it back.
            self._clear_live_card(finished=True)
        else:
            return False
        _LOGGER.info("Handled live-card action %s", action)
        return True

    async def async_stop_print(self) -> None:
        """Stop the current print.

        Shared with the stop button entity so the notification action and the
        dashboard cannot drift apart. The paused flag is deliberately not forced
        here; telemetry reflects idle soon enough.
        """
        if not await self.ensure_connected():
            _LOGGER.warning("Cannot execute stop command: printer not connected")
            return
        await self.client.send_set_retry(stop=1)

    def notifier_tick(self) -> None:
        """Clear a live card the printer has stopped reporting on.

        Driven by the existing periodic check in `__init__.py` rather than a new
        timer. Every other transition is caused by an incoming frame, so without
        this a card would sit on the phone forever showing a print that silently
        stopped -- a pulled plug, a crashed printer, a dead network.
        """
        if not self._live_card.card_active:
            return
        idle = self.hass.loop.time() - self.client.last_rx_monotonic()
        if idle < NOTIFY_LIVE_STALE_CLEAR_SECS:
            return
        _LOGGER.info(
            "No printer telemetry for %.0fs; clearing the live print card", idle
        )
        self._clear_live_card()

    async def _async_load_notify_strings(self) -> None:
        """Load the translated notification strings, once per entry load.

        Notification bodies are composed here rather than rendered in the
        frontend, and an integration is never told *which user* a notification
        is for -- so the only language available is the server's. That is a
        documented limitation, not a reason to hardcode English: the strings
        still live in strings.json, and the bus events exist for anyone who
        needs per-user text. Home Assistant caches these, so the call is cheap
        after the first.
        """
        if self._notify_strings is not None:
            return
        language = getattr(getattr(self.hass, "config", None), "language", None) or "en"
        # "common" rather than a category of our own: hassfest validates
        # strings.json against a fixed set of top-level keys and rejects
        # anything else, and `common` is the only one shaped as a flat
        # slug -> string bag. It is namespaced per integration either way.
        prefix = f"component.{DOMAIN}.common."
        try:
            raw = await async_get_translations(self.hass, language, "common", {DOMAIN})
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Could not load notification strings")
            self._notify_strings = {}
            return

        self._notify_strings = {
            key[len(prefix) :]: value
            for key, value in (raw or {}).items()
            if key.startswith(prefix)
        }
        if not self._notify_strings:
            _LOGGER.error(
                "No notification strings available for language %s; "
                "notifications are disabled until this is fixed",
                language,
            )

    def _t(self, key: str, /, **values: Any) -> str:
        """Resolve one translated notification string.

        `key` is positional-only: the error template substitutes a placeholder
        literally named `key` (the printer's error key), which would otherwise
        collide with this parameter.

        A translation whose placeholders do not match returns empty rather than
        raising: callers drop empty segments, so one bad string in one language
        costs a line of text instead of the whole notification.
        """
        template = (self._notify_strings or {}).get(key)
        if not template:
            _LOGGER.debug("No notification string for %r", key)
            return ""
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError):
            _LOGGER.warning(
                "Notification string %r does not match its placeholders; "
                "check that translation",
                key,
            )
            return ""

    def _template_values(self, name: str, /, **extra: Any) -> dict[str, str]:
        """The placeholders one notification can fill, already rendered.

        All of it read from one telemetry frame, so a template cannot mix a
        percentage from this second with an estimate from the last. Durations
        and the filament length go through the same translated formatters the
        shipped sentences use, which is what keeps "4h 12m" and "1.2 m" spelled
        the same way whoever composed the text.

        A value the printer has not reported is the empty string rather than a
        zero or a dash. That is what an optional `[...]` segment tests, and the
        reason it can: a real 0% is "0", an unknown one is "".

        Narrowed to `TEMPLATE_FIELDS[name]` on the way out, so the keys of what
        this returns *are* the placeholders that notification may use -- which
        is what lets the renderer reject the rest without being told twice, and
        what the options flow lists under the field.

        `extra` overrides, for the values the frame cannot supply: the minutes
        on the finishing-soon reminder, the error key, and the file name and
        progress of a print whose stop has already reset both.
        """
        d = self.data or {}
        strings = self._notify_strings or {}
        progress = self._notify_progress()
        layer = self._int_or_none(d.get("layer"))
        total_layers = self._int_or_none(d.get("TotalLayer"))
        code = self._error_code(d)
        values: dict[str, str] = {
            "device": self._notify_title(),
            "filename": display_filename(d.get("printFileName")),
            "progress": "" if progress is None else str(progress),
            "layer": "" if layer is None else str(layer),
            "total_layers": "" if total_layers is None else str(total_layers),
            "eta": format_duration(self._print_seconds_left(d), strings),
            "elapsed": format_duration(d.get("printJobTime"), strings),
            "filament": format_filament_length(
                d.get("usedMaterialLength"), strings.get("filament_length")
            ),
            "nozzle": self._whole_degrees(d.get("nozzleTemp")),
            "bed": self._whole_degrees(d.get("bedTemp0")),
            "state": self._job_state(),
            # 0 is "no error", so it renders empty and an optional segment
            # holding it disappears rather than announcing error 0.
            "error_code": str(code) if code else "",
            "error_key": "",
            "minutes": "",
        }
        for key, value in extra.items():
            values[key] = "" if value is None else str(value)
        allowed = TEMPLATE_FIELDS.get(name, ())
        return {key: value for key, value in values.items() if key in allowed}

    @staticmethod
    def _whole_degrees(value: Any) -> str:
        """A temperature for a notification body, or empty when there is none.

        Rounded: a notification is read at a glance, and the printer reports a
        decimal of noise that says nothing at that distance.
        """
        number = safe_float(value)
        if number is None or not math.isfinite(number):
            return ""
        return str(round(number))

    def _custom_message(self, name: str, /, **extra: Any) -> str:
        """The user's own text for one notification, or empty to use ours.

        The single gate for every template, so "a template that cannot render
        falls back to the shipped sentence" is one rule in one place rather than
        six call sites that each have to remember it.

        Nothing is computed for a notification with no template: this is on the
        live card's path, which runs on every WebSocket frame, and building the
        value bag there would mean formatting six numbers per frame to throw
        them away. `name` is positional-only so an `extra` value could never
        collide with it, the same reason `_t` is.
        """
        template = self._notify_templates.get(name)
        if not template:
            return ""
        text = render_user_template(template, self._template_values(name, **extra))
        if not text:
            # Once per template rather than once per push: the live card is
            # pushed up to 600 times a job, and a template that renders to
            # nothing usually does so for a whole print.
            warned = (name, template)
            if warned not in self._notify_template_warned:
                self._notify_template_warned.add(warned)
                _LOGGER.warning(
                    "Custom %s notification text could not be rendered; "
                    "using the built-in text instead",
                    name,
                )
        return text

    def _notify_title(self) -> str:
        """Printer name, used as the notification title.

        Has to be stable for the whole life of a live card: Android requires a
        title and will not update one after the activity has started, so
        anything job-specific belongs in the body instead.

        Falls back to the host rather than a generic string. Telemetry arrives
        incrementally and priming only waits for a file name and progress, so a
        card can start before `hostname` has been reported -- and because the
        title is then frozen, a generic fallback would leave the whole job
        labelled with the generic fallback and no way to tell two machines apart.
        """
        d = self.data or {}
        return str(
            d.get("hostname")
            or d.get("model")
            or self.client._host
            or self._t("title_fallback")
        )

    def notify_options_changed(self, options: Any) -> None:
        """Take the live card off any phone the new options no longer cover.

        Whatever happens next -- an in-place apply or a full reload -- this is
        the last moment anything knows which targets are carrying a card, so a
        phone that is being dropped has to be told here or it keeps a card that
        will never update and never go away.

        Two ways to be dropped, and both are handled: the card switched off (or
        its last target removed), and a target removed from a list of several.
        The second one used to be missed entirely, because "still wanted" was
        asked of the setting rather than of each phone.

        A target that survives is deliberately left alone. It keeps the card it
        has, and the next frame refreshes it in place -- dismissing first would
        make it flicker and spend an iOS push-to-start slot for nothing.
        """
        if not self._live_card.card_active:
            return
        try:
            wanted = bool(options.get(CONF_NOTIFY_LIVE, False))
            keep = set(coerce_targets(options)) if wanted else set()
        except Exception:  # pylint: disable=broad-except
            return

        dropped = [t for t in self._notify_targets if t not in keep]
        if not dropped:
            return
        if not keep:
            _LOGGER.info("Live print card switched off; dismissing it")
            self._clear_live_card()
            return

        _LOGGER.info(
            "Dismissing the live print card on %d target(s) it was removed from",
            len(dropped),
        )
        payload = build_clear_payload(f"{self._notify_tag_base()}_live")
        for target in dropped:
            if is_mobile_target(target) and is_live_capable(self._target_os(target)):
                self.hass.async_create_task(
                    self._async_deliver_one(target, payload)
                )

    def notifications_only_change(self, options: Mapping[str, Any]) -> bool:
        """Whether an options update touched nothing but the notification path.

        Compared against the options this coordinator was last built from, not
        against defaults: the question is what the user just changed, and a
        setting they have never touched is not a change.

        Anything unrecognised counts as needing a reload, including nothing at
        all -- an update that leaves the options identical is a change to the
        entry's `data`, which is where the host lives.
        """
        previous = self._loaded_options
        if previous is None:
            return False
        touched = {
            key
            for key in set(previous) | set(options)
            if previous.get(key) != options.get(key)
        }
        return bool(touched) and touched <= NOTIFY_ONLY_OPTION_KEYS

    def apply_notification_options(self, options: Any) -> None:
        """Adopt new notification options without reloading the entry.

        A reload drops the WebSocket, flips every entity unavailable and
        restarts the camera stream, which is a heavy price for changing the
        wording of a notification -- and the options flow now saves each page as
        it is submitted, so that price used to be paid several times while
        someone edited their settings.

        The card is *resynced* rather than left alone: its text, its buttons and
        its pictures all come from these options, and the state is cleared so
        the next telemetry frame re-pushes a card built from the new ones. That
        replaces the card in place, on its own tag, exactly as a mid-print
        restart does -- rather than leaving the old text on the phone until the
        five-minute refresh comes round.
        """
        self.notify_options_changed(options)
        resync = self._live_card.card_active
        self._load_options()
        if resync and self._notify_live and self._notify_targets:
            self._live_card.clear()
        _LOGGER.info("Notification settings applied without a reload")

    def _notify_tag_base(self) -> str:
        """Stable tag prefix for this printer.

        Derived from the config entry id and never from the host: the host is an
        IP address and dots are illegal in a tag. It also has to survive a Home
        Assistant restart, because that is what lets an existing card be
        replaced rather than duplicated.
        """
        return notify_tag_base(self.entry_id, self.client._host)

    async def _notify_event(self, message: str, *, kind: str) -> None:
        """Build and dispatch one of the one-shot lifecycle notifications.

        The single chokepoint for them, which is what
        `tools/tests/test_notifications.py` monkeypatches so the gating rules --
        the completion re-arm from b2ac2ea and the issue #112 priming window --
        can be driven without any service layer underneath.
        """
        tag_base = self._notify_tag_base()
        title = self._notify_title()
        links = self._notify_links()

        if kind in (ALERT_ERROR, ALERT_RUNOUT):
            payload = build_alert_payload(
                tag=f"{tag_base}_alert",
                title=title,
                message=message,
                kind=kind,
                channel=self._t(NOTIFY_CHANNEL_KEY_ALERT),
                group=tag_base,
                # A picture of the bed is the whole point of a failure alert you
                # read from another room.
                visuals=self._notify_media(include_snapshot=True),
                links=links,
            )
            self._alert_showing = True
        elif kind == EVENT_SOON:
            # Its own tag and channel. On the shared `_event` tag the completion
            # banner replaced this reminder minutes later, so the one
            # notification whose whole purpose is "go and look at the printer"
            # was the one that vanished. It now sits alongside the live card
            # instead, and being a separate channel it can make a sound while
            # the card stays quiet.
            payload = build_event_payload(
                tag=f"{tag_base}_soon",
                title=title,
                message=message,
                kind=kind,
                channel=self._t(NOTIFY_CHANNEL_KEY_SOON),
                group=tag_base,
                # No bed snapshot: the print is not finished, and the preview
                # already says what is on the plate.
                visuals=self._notify_media(include_snapshot=False),
                links=links,
            )
        else:
            # Terminal. Posted on the live card's own tag so it *replaces* the
            # card in place rather than arriving beside a card that has to be
            # dismissed separately -- and with no preceding clear, which would
            # make it visibly flicker.
            #
            # A confirmation, not a last refresh of the card: no progress bar,
            # no countdown, no action buttons. `build_event_payload` is what
            # leaves the bar out, for every flavour and on purpose.
            payload = build_event_payload(
                tag=f"{tag_base}_live",
                title=title,
                message=message,
                kind=kind,
                channel=self._t(NOTIFY_CHANNEL_KEY_DONE),
                group=tag_base,
                visuals=self._notify_media(include_snapshot=True),
                links=links,
                ends_activity=True,
            )
            # Dismiss the card first, then post this in its place, both on the
            # same tag and in that order.
            #
            # Replacing it by tag identity alone was the earlier design and it
            # left the card stuck: a `live_update` notification is an ongoing
            # one on Android, and posting an ordinary banner over it does not
            # take it down -- a print that had finished minutes ago sat at 95%
            # while its own completion notice was delivered successfully. A
            # brief flicker is a small price for the card actually going away.
            self._card_dismiss_owed = False
            self._replace_card_with(payload, kind=kind)
            return

        self._notify_dispatch(payload, kind=kind)

    def _completion_message(self, d: dict[str, Any], job: str) -> str:
        """Completion text, naming the filament used when the printer said.

        Two whole sentences rather than one sentence plus a bolted-on fragment,
        so each reads naturally in every language -- and so the shorter one is
        a complete sentence rather than a truncated version of the longer.
        Falls back to it whenever the length is missing, which is what an
        aborted or very short job reports.
        """
        custom = self._custom_message("completed")
        if custom:
            return custom

        device = self._notify_title()
        filament = format_filament_length(
            d.get("usedMaterialLength"), (self._notify_strings or {}).get("filament_length")
        )
        if filament:
            detailed = self._t(
                "completed_detailed", device=device, filament=filament
            )
            if detailed:
                return detailed
        return self._t("completed", device=device)

    def _notify_progress(self) -> int | None:
        """Progress for a notification body, or None when the printer has not said."""
        d = self.data or {}
        progress = d.get("printProgress")
        if progress is None:
            progress = d.get("dProgress")
        value = safe_float(progress)
        if value is None or not math.isfinite(value):
            return None
        return int(value)

    def _target_os(self, target: str) -> str | None:
        """The companion `os_name` behind a notify target, or None if unknown.

        `mobile_app` names its notify service after the slugified device name,
        so the entry can be found by slugifying it back. Matching on that rather
        than guessing from the service name, because "macbookairlukas" is not
        distinguishable from a phone by inspection.
        """
        if target in self._target_os_cache:
            return self._target_os_cache[target]

        slug = notify_service_slug(target)
        found: str | None = None
        if slug:
            entries = getattr(self.hass.config_entries, "async_entries", None)
            for entry in (entries("mobile_app") if entries else ()):
                data = getattr(entry, "data", None) or {}
                if slugify(str(data.get("device_name", ""))) == slug:
                    found = data.get("os_name")
                    break
        self._target_os_cache[target] = found
        return found

    def _replace_card_with(self, payload: dict[str, Any], *, kind: str) -> None:
        """Dismiss the live card and post `payload` in its place, in that order.

        One task per target, each awaiting the dismissal before the banner.
        Dispatching them as two independent tasks would leave the order to the
        event loop, and a dismissal that landed second would take the banner
        down with it -- turning a stuck card into no notification at all.

        Still never awaited from here: `ws_client` awaits `_on_message` inline
        in its receive loop, so blocking on an HTTPS round trip would let
        `last_rx_monotonic()` go stale and flip every entity unavailable.
        """
        clear = build_clear_payload(f"{self._notify_tag_base()}_live")
        # The same live-capability gate the card itself was pushed under. A
        # macOS companion is skipped by `live_only`, so it never received the
        # card -- sending it the dismiss sentinel clears a tag it does not have,
        # and the sentinel is only meaningful to a client that consumes it.
        targets = [
            t for t in self._notify_targets
            if is_mobile_target(t) and is_live_capable(self._target_os(t))
        ]
        for target in targets:
            self.hass.async_create_task(
                self._async_replace_one(target, clear, payload)
            )
        _LOGGER.info(
            "Notification dispatched (%s, replacing the card) to %d target(s)",
            kind,
            len(targets),
        )
        # Everything else just gets the banner: a non-mobile target cannot carry
        # a tag at all, and a live-incapable one has no card to replace.
        for target in self._notify_targets:
            if target not in targets:
                self.hass.async_create_task(
                    self._async_deliver_one(target, payload)
                )

    async def _async_replace_one(
        self, target: str, clear: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        await self._async_deliver_one(target, clear)
        await self._async_deliver_one(target, payload)

    def _notify_dispatch(
        self,
        payload: dict[str, Any],
        *,
        kind: str = "event",
        mobile_only: bool = False,
        live_only: bool = False,
    ) -> None:
        """Fan a payload out to every configured target without blocking.

        Deliberately not a coroutine that awaits the sends. `ws_client` awaits
        `_on_message` inline in its receive loop, and a notify call is an HTTPS
        POST to a push relay for mobile_app targets -- awaiting one there stalls
        the loop, lets `last_rx_monotonic()` go stale and flips every entity
        unavailable at STALE_AFTER_SECS. One task per target, never awaited.
        """
        targets = self._notify_targets
        if not targets:
            return

        sent_to = 0
        for target in targets:
            if (mobile_only or live_only) and not is_mobile_target(target):
                # Live-card keys are meaningless to anything but the companion
                # app, so a progress push has nothing to say to these.
                _LOGGER.debug("Skipping %s push for non-mobile target %s", kind, target)
                continue
            if live_only and not is_live_capable(self._target_os(target)):
                # macOS has no live-card surface, so every refresh would arrive
                # as another ordinary banner that supersedes nothing -- twelve
                # an hour for the length of the print.
                _LOGGER.debug(
                    "Skipping %s push for %s: %s cannot render a live card",
                    kind,
                    target,
                    self._target_os(target),
                )
                continue
            sent_to += 1
            self.hass.async_create_task(self._async_deliver_one(target, payload))

        if not sent_to:
            return
        # INFO omits the target list and the body on purpose: both end up in
        # user-submitted logs, and entity ids plus print file names are theirs,
        # not ours. DEBUG carries them for anyone debugging their own setup.
        #
        # Live-card pushes stay at DEBUG: there are ~20 per print, and they would
        # otherwise bury the handful of lines that describe something happening.
        if not kind.startswith("live"):
            _LOGGER.info(
                "Notification dispatched (%s) to %d target(s)", kind, sent_to
            )
        _LOGGER.debug(
            "Notification (%s) targets=%s body=%.200s",
            kind,
            targets,
            payload.get("message", ""),
        )

    async def _async_deliver_one(self, target: str, payload: dict[str, Any]) -> None:
        """Deliver one payload to one target, tolerating a dead target."""
        message = payload.get("message", "")
        title = payload.get("title")
        data = payload.get("data")

        try:
            state = (
                self.hass.states.get(target) if target.startswith("notify.") else None
            )
            if state is not None and getattr(state, "domain", None) == "notify":
                # A notify *entity*. `notify.send_message` is the only service
                # for these and its schema has no `data` field, so an entity
                # target can never carry a tag -- which also means the dismiss
                # sentinel would arrive as visible body text.
                if message == CLEAR_NOTIFICATION_MARKER:
                    _LOGGER.debug(
                        "Not sending the dismiss sentinel to notify entity %s: "
                        "send_message cannot carry a tag",
                        target,
                    )
                    return
                if data:
                    _LOGGER.debug(
                        "Dropping %d unsupported key(s) for notify entity %s: %s",
                        len(data),
                        target,
                        ", ".join(sorted(data)),
                    )
                entity_data: dict[str, Any] = {"entity_id": target, "message": message}
                if title:
                    entity_data["title"] = title
                await self.hass.services.async_call(
                    "notify", "send_message", entity_data
                )
                return

            if "." not in target:
                # The options flow accepts free text, and this used to fail
                # completely silently: no error, no log, no notification.
                _LOGGER.warning(
                    "Ignoring notify target %r: expected the form domain.service",
                    target,
                )
                return

            domain, service = target.split(".", 1)
            if not is_mobile_target(target):
                if message == CLEAR_NOTIFICATION_MARKER:
                    _LOGGER.debug(
                        "Not sending the dismiss sentinel to %s: it would render "
                        "as visible text",
                        target,
                    )
                    return
                # Strict-schema platforms reject unknown keys and fail the whole
                # call, and the relative /api/ media URLs only authenticate from
                # the companion app anyway.
                data = None

            service_data: dict[str, Any] = {"message": message}
            if title:
                service_data["title"] = title
            if data:
                # Only the mobile branch reaches here with data still attached,
                # and that is the one the FCM string rule applies to.
                service_data["data"] = stringify_data(data)
                _warn_on_unsendable(service_data["data"], target)
            await self.hass.services.async_call(domain, service, service_data)
        except Exception:  # pylint: disable=broad-except
            # One unreachable phone must not starve the others.
            _LOGGER.exception("Failed to send notification to %s", target)

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
                            # Via the helper, not a direct write: on a K2 Base the
                            # WS feed pops targetBoxTemp:0, so this poll is the
                            # only source of the field that gates the chamber
                            # control, and it has to fire discovery itself.
                            self.merge_telemetry({"targetBoxTemp": target})
                            self.async_update_listeners()
        except Exception as e:
            # Moonraker might be disabled or port 7125 blocked; fail silently but log debug
            _LOGGER.debug("Failed to poll Moonraker for extras: %s", e)
