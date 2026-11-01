"""WebSocket client for Creality 3D printers."""
from __future__ import annotations

import asyncio
import json
import logging
import random
import socket
import time
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosed

from .const import (
    GCODE_FILE_REQUEST,
    GCODE_FILE_RESPONSE,
    RETRY_MIN_BACKOFF,
    RETRY_MAX_BACKOFF,
    RETRY_BACKOFF_MULTIPLIER,
    HEARTBEAT_SECS,
    PROBE_ON_SILENCE_SECS,
    WS_SUBPROTOCOL,
    WS_URL_TEMPLATE,
)
from .utils import coerce_numbers

_LOGGER = logging.getLogger(__name__)
OnMessage = Callable[[dict[str, Any]], Awaitable[None]]

# Periodic “get” cadences (mirror browser behavior)
GET_REQPRINTERPARA_SEC = 5.0         # curPosition, autohome, etc.
GET_PRINT_OBJECTS_SEC = 2.0          # objects/exclusions/current object
GET_BOXS_INFO_SEC = 300.0             # CFS box info (temp/humidity/filaments) every 5m
# A connection must survive this long before we consider it stable enough to
# reset the failure/backoff counters. Prevents fast connect/drop flapping from
# masquerading as healthy reconnects.
STABLE_CONNECT_SECS = 10.0
# How often the switch is re-read while it says the printer is off.
POWER_OFF_POLL_SECS = 10.0
# Largest frame accepted. The G-code listing reply carries every file on the
# printer, about 150 KiB per 200 files, and the library default of 1 MiB closed
# the connection (code 1009) on any printer holding more than ~1300. Bounded
# rather than unlimited: this is still a frame from the network.
WS_MAX_MESSAGE_BYTES = 16 * 2**20



## number coercion handled by utils.coerce_numbers


class KClient:
    """Resilient WS client with backoff, heartbeat 'ok', periodic GETs, and staleness tracking."""

    def __init__(self, host: str, on_message: OnMessage):
        self._host = host
        # The URL for a host; the connect loop passes the resolved address.
        self._url = lambda host=None: WS_URL_TEMPLATE.format(host=host or self._host)
        self._on_message = on_message
        self._check_power_status: Callable[[], bool] | None = None
        self._state: dict[str, Any] = {}

        self._task: asyncio.Task | None = None
        self._ws: websockets.client.ClientConnection | None = None  # type: ignore[attr-defined]
        self._stop = asyncio.Event()
        self._connected_once = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._last_rx = 0.0
        # Set once the current outage has been reported; cleared by data.
        self._warned_unreachable = False

        self._hb_task: asyncio.Task | None = None
        self._tick_task: asyncio.Task | None = None

        # event that indicates a live socket is present
        self._ws_ready = asyncio.Event()

        # Flag to force a connection attempt even if power is off (manual reconnect)
        self._force_connect = False

        # Diagnostics / Metrics
        self.reconnect_count = 0
        self.msg_count = 0
        self.last_error: str | None = None
        self.uptime_start = 0.0

    @property
    def host(self) -> str:
        """Return the host address."""
        return self._host

    @property
    def is_connected(self) -> bool:
        """Return True if WebSocket is connected."""
        return self._ws is not None and self._ws_ready.is_set()

    def get_url(self) -> str:
        """Return the current WebSocket URL."""
        return self._url() if self._url else "unknown"

    def has_connected_once(self) -> bool:
        """Return True if we have connected at least once."""
        return self._connected_once.is_set()

    def is_task_running(self) -> bool:
        """Return True if the main loop task is running."""
        return self._task is not None and not self._task.done()

    # ---------- lifecycle ----------
    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="K-ws-loop")

    async def stop(self) -> None:
        """Stop the client and close connections."""
        self._stop.set()
        for t in (self._hb_task, self._tick_task):
            if t:
                t.cancel()
        ws = self._ws
        if ws:
            try:
                await ws.close(code=1000, reason="shutdown")
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._task = None
            
    def _is_benign_close(self, exc: Exception) -> bool:
        """Return True for expected/normal shutdown / harmless closes."""
        if isinstance(exc, (ConnectionClosedOK, asyncio.CancelledError)):
            return True
        if isinstance(exc, ConnectionClosed):
            try:
                if getattr(exc, "code", None) == 1000:
                    return True
            except Exception:
                pass
        msg = str(exc).lower()
        if (
            "no close frame received" in msg
            or "connection closed ok" in msg
            or "code = 1000" in msg
            or "sent 1000" in msg
        ):
            return True
        if self._stop.is_set():
            return True
        return False

    async def wait_first_connect(self, timeout: float = 5.0) -> bool:
        try:
            await asyncio.wait_for(self._connected_once.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def wait_connected(self, timeout: float) -> bool:
        """Wait for a live WebSocket connection (used by retrying sender)."""
        try:
            await asyncio.wait_for(self._ws_ready.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def reconnect(self):
        """Force a reconnection to the WebSocket server."""
        _LOGGER.info("Re-establishing WebSocket connection to retrieve latest state.")
        self._force_connect = True
        await self.stop()
        await self.start()

    # ---------- connectivity loop ----------
    async def _async_resolve_host(self) -> str:
        """The host's IPv4 address, preferred as before, or the host as given.

        Resolved through the event loop's executor-backed `getaddrinfo`. The
        old synchronous lookup ran on the loop itself at every connect
        attempt: with a `.local` name and the printer switched off, each retry
        could hold Home Assistant for seconds.
        """
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                self._host, None, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
        except (OSError, UnicodeError):
            return self._host
        return infos[0][4][0] if infos else self._host

    async def _loop(self) -> None:
        backoff = RETRY_MIN_BACKOFF
        connect_failures = 0
        # For power-switch users: use standard backoff
        # For non-power-switch users: use fixed short retry interval for continuous detection
        use_fixed_retry = not self._check_power_status
        fixed_retry_interval = 60.0  # Fixed 60s retry when no power switch configured
        max_backoff = RETRY_MAX_BACKOFF if self._check_power_status else fixed_retry_interval
        
        while not self._stop.is_set():
            # --- Power Saving Check (Start of Loop) ---
            # While the switch says the printer is off, poll the switch instead
            # of the printer, with the backoff reset so the first attempt after
            # power returns is immediate. A manual Reconnect skips the check
            # once. 0.9.1 had this inverted: only a forced attempt checked, so
            # an unforced loop backed off to 300 s against a dark printer.
            forced = self._force_connect
            self._force_connect = False
            if forced:
                _LOGGER.info("Forcing connection attempt (manual reconnect)")
            elif self._check_power_status and self._check_power_status():
                _LOGGER.debug(
                    "Printer power is OFF; checking again in %.0fs host=%s",
                    POWER_OFF_POLL_SECS,
                    self._host,
                )
                backoff = RETRY_MIN_BACKOFF
                connect_failures = 0
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=POWER_OFF_POLL_SECS)
                except asyncio.TimeoutError:
                    pass
                continue

            connected_this_attempt = False
            try:
                url = self._url(await self._async_resolve_host())
                _LOGGER.debug("K WS connecting host=%s url=%s", self._host, url)
                # Disable library pings; we do app-level heartbeat + periodic GETs.
                # Advertise the printer web UI's subprotocol for handshake parity.
                async with websockets.connect(
                    url,
                    ping_interval=None,
                    subprotocols=[WS_SUBPROTOCOL],
                    max_size=WS_MAX_MESSAGE_BYTES,
                ) as ws:
                    self._ws = ws
                    connected_this_attempt = True
                    _LOGGER.debug("K WS handshake connected host=%s url=%s", self._host, url)

                    # Store connect time to calculate duration later. Do NOT set
                    # _ws_ready/_connected_once/_last_rx here: readiness and
                    # availability require actual data, not just a TCP handshake.
                    self.uptime_start = time.monotonic()
                    self.reconnect_count += 1

                    # background tasks
                    self._hb_task = asyncio.create_task(self._heartbeat(), name="K-ws-heartbeat")
                    self._tick_task = asyncio.create_task(self._periodic_gets(), name="K-ws-ticker")

                    async for raw in ws:
                        # websockets>=15: text is str, binary is bytes
                        if isinstance(raw, (bytes, bytearray)):
                            text = raw.decode("utf-8", "ignore")
                        else:
                            text = raw

                        # Fast-path: if it's exactly "ok", ignore
                        if text == "ok":
                            continue

                        # Try parse JSON
                        try:
                            payload: Any = json.loads(text)
                        except Exception:
                            # Not JSON; ignore
                            continue

                        # Heartbeat handling
                        if isinstance(payload, dict) and payload.get("ModeCode") == "heart_beat":
                            self._mark_ready(url)
                            # ACK immediately; literal 'ok' (no JSON)
                            try:
                                await ws.send("ok")
                            except Exception:
                                pass
                            continue

                        if isinstance(payload, dict):
                            self._mark_ready(url)
                            frame = self._absorb(payload)
                            try:
                                await self._on_message(frame)
                            except Exception:
                                _LOGGER.exception("K on_message failed host=%s", self._host)
                        else:
                            _LOGGER.debug("K WS unexpected frame type: %r", type(payload))

            except asyncio.CancelledError:
                break
            except Exception as exc:
                short_lived = (
                    connected_this_attempt
                    and time.monotonic() - self.uptime_start < STABLE_CONNECT_SECS
                )
                connect_failures += 1

                # Check power status before logging loud errors.
                # If power is OFF, we treat it as expected (debug only).
                is_off = self._check_power_status and self._check_power_status()
                
                if is_off:
                    _LOGGER.debug(
                        "K WS closed/failed (power OFF) host=%s reason=%s", self._host, exc
                    )
                elif self._is_benign_close(exc):
                    _LOGGER.debug(
                        "K WS closed host=%s reason=%s short_lived=%s attempt=%d",
                        self._host, exc, short_lived, connect_failures,
                    )
                else:
                    # Log a single warning after 3 failures (confirms it's not transient)
                    # All other failures are debug-only to avoid log spam
                    if connect_failures <= 3:
                        _LOGGER.warning(
                            "K WS connection failed host=%s (printer likely off, retrying silently)",
                            self._host
                        )
                    else:
                        _LOGGER.debug("K WS connection error host=%s err=%s (attempt=%d)", self._host, exc, connect_failures)
                self.last_error = str(exc)
            finally:
                # A session that survived long enough was healthy, however it
                # ended. Resetting only on a clean close meant a Wi-Fi blip
                # after hours of uptime waited out the backoff of the failures
                # before it.
                if (
                    connected_this_attempt
                    and time.monotonic() - self.uptime_start >= STABLE_CONNECT_SECS
                ):
                    connect_failures = 0
                    backoff = RETRY_MIN_BACKOFF

                # cleanup on disconnect
                for t in (self._hb_task, self._tick_task):
                    if t:
                        t.cancel()
                self._hb_task = self._tick_task = None

                self._ws = None
                self._ws_ready.clear()


            # If no power switch AND we've failed > 5 times, assume printer is off -> slow poll
            if use_fixed_retry and connect_failures >= 5:
                sleep_for = fixed_retry_interval
            else:
                # Exponential backoff for first few failures (or always if power switch is used)
                jitter = random.uniform(0.0, 0.4)
                sleep_for = min(backoff * (RETRY_BACKOFF_MULTIPLIER + jitter), max_backoff)
            
            power_is_off = bool(self._check_power_status and self._check_power_status())
            if power_is_off:
                _LOGGER.debug("K WS not reconnecting: power is OFF host=%s", self._host)
            elif (
                not self._warned_unreachable
                and (not use_fixed_retry or connect_failures < 5)
                and backoff >= (RETRY_MAX_BACKOFF * 0.9)
            ):
                # Once per outage. This used to announce an mDNS fallback that
                # never existed, and repeated every five minutes for as long as
                # the printer stayed unreachable (#84).
                self._warned_unreachable = True
                _LOGGER.warning(
                    "K WS connection failing repeatedly (host=%s); retrying every %.0fs",
                    self._host,
                    sleep_for,
                )

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                # Expected timeout
                pass
            
            if not use_fixed_retry or connect_failures < 5:
                backoff = min(sleep_for, max_backoff)

        _LOGGER.debug("K WS loop exited host=%s", self._host)

    def _mark_ready(self, url: str) -> None:
        """Mark the connection ready on the first valid frame.

        Readiness (and entity availability, which keys off RX recency) requires
        actual printer data, not just a completed TCP/WS handshake.
        """
        self._last_rx = time.monotonic()
        if not self._ws_ready.is_set():
            self._ws_ready.set()
            self._connected_once.set()
            self._warned_unreachable = False
            _LOGGER.info("K WS ready host=%s url=%s", self._host, url)

    async def _heartbeat(self):
        """Monitor connection health by checking RX activity.
        Some printers do not implement WebSocket Pings correctly, so we use
        application-level staleness check (Watchdog) instead.
        """
        try:
            # Initial probe on silence (e.g. after fresh connect). Until the
            # first frame arrives _last_rx is stale, so measure silence from the
            # connect time to avoid a premature "dead connection" verdict.
            await asyncio.sleep(PROBE_ON_SILENCE_SECS)
            if self._stop.is_set():
                return
            if time.monotonic() - max(self._last_rx, self.uptime_start) > PROBE_ON_SILENCE_SECS:
                try:
                    await self._send_json({"method": "get", "params": {"ReqPrinterPara": 1}})
                except Exception:
                    pass

            while True:
                await asyncio.sleep(HEARTBEAT_SECS)
                if self._stop.is_set():
                    return
                ws = self._ws
                if not ws:
                    break

                now = time.monotonic()
                silence_duration = now - max(self._last_rx, self.uptime_start)

                # If connection is quiet, try to provoke a response w/ benign command
                if silence_duration > HEARTBEAT_SECS:
                    _LOGGER.debug("K WS quiet for %.1fs, sending probe", silence_duration)
                    try:
                        await self._send_json({"method": "get", "params": {"ReqPrinterPara": 1}})
                    except Exception:
                        # Connection may be dead; ignore send errors, rely on staleness detection
                        pass
                
                # If STILL no data for too long (3x heartbeat), assume dead and reconnect
                if silence_duration > (HEARTBEAT_SECS * 3):
                    _LOGGER.warning("K WS connection dead (no RX for %.1fs); reconnecting", silence_duration)
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    break
        except asyncio.CancelledError:
            return

    async def _periodic_gets(self):
        """Mirror the web UI's periodic GETs so the printer keeps streaming state."""
        try:
            await asyncio.sleep(2.0)
            now = time.monotonic()
            # Back-date each timer by its own interval so the first poll of each
            # fires on the first ready iteration instead of a full interval after
            # connect. Critical for CFS: boxsInfo is only sent on request (never
            # in the regular stream), so a `now`-initialised t_cfs left CFS
            # sensors unavailable for the full 5-minute interval after every
            # (re)connect (issue #99). The _ws_ready gate below still prevents
            # sending before the connection has proven it's talking.
            t_para = now - GET_REQPRINTERPARA_SEC
            t_objs = now - GET_PRINT_OBJECTS_SEC
            t_cfs = now - GET_BOXS_INFO_SEC
            # Staggered loop to avoid bursts
            while True:
                now = time.monotonic()
                ws = self._ws
                if not ws:
                    break
                if self._stop.is_set():
                    break
                # Hold off issuing GETs until the printer has proven it's talking.
                if not self._ws_ready.is_set():
                    await asyncio.sleep(0.2)
                    continue
                if now - t_para >= GET_REQPRINTERPARA_SEC:
                    try:
                        await self._send_json({"method": "get", "params": {"ReqPrinterPara": 1}})
                    except Exception:
                        pass
                    t_para = now

                if now - t_objs >= GET_PRINT_OBJECTS_SEC:
                    try:
                        await self._send_json({"method": "get", "params": {"reqPrintObjects": 1}})
                    except Exception:
                        pass
                    t_objs = now

                # Only request CFS info if we know CFS is connected or haven't checked recently
                if now - t_cfs >= GET_BOXS_INFO_SEC:
                    # If we have state, check cfsConnect. If not yet known, poll anyway to discover.
                    cfs_connected = self._state.get("cfsConnect")
                    if cfs_connected is None or cfs_connected == 1:
                        try:
                            await self.request_boxs_info()
                        except Exception:
                            pass
                    t_cfs = now

                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            return

    def _absorb(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Merge one frame into the cumulative state; return what is handed on.

        The whole state, not the frame: the printer sends deltas, and the
        coordinator expects every field it has ever seen.
        """
        self._state.update(coerce_numbers(payload))
        self.msg_count += 1
        frame = dict(self._state)
        # One-shot, not telemetry: the reply lists every G-code file on the
        # printer (~150 KiB on a K1C). Left in the cumulative state it would
        # ride on every later frame, and the coordinator would rescan the whole
        # listing once per frame on the receive path.
        self._state.pop(GCODE_FILE_RESPONSE, None)
        return frame

    # ---------- commanded values ----------
    def reported(self, key: str) -> Any:
        """The value the printer last reported for one telemetry key."""
        return self._state.get(key)

    def assume(self, values: dict[str, Any]) -> None:
        """Fold values just commanded into the state every frame is built from.

        Each frame hands the coordinator the whole cumulative state, so a value
        set on the coordinator alone lasted only until the next frame of any
        kind, which still carried the old one: a printer slow to echo a new
        target showed it set and then back at 0 (#132). The printer's next
        report of the key replaces it, as any report does.
        """
        self._state.update(values)

    # ---------- public send ----------
    async def request_boxs_info(self) -> None:
        """Ask the printer to send boxsInfo now."""
        await self._send_json({"method": "get", "params": {"boxsInfo": 1}})

    async def request_gcode_file_info(self) -> None:
        """Ask the printer for its sliced-G-code metadata listing.

        Deliberately not in `_periodic_gets`: the reply carries every file on
        the printer, so the coordinator asks only when the running file changes.
        """
        await self._send_json({"method": "get", "params": {GCODE_FILE_REQUEST: 1}})
    async def send_set_retry(self, *, wait_reconnect: float = 6.0, **params: Any) -> None:
        """
        Robust sender for user actions: try once; if the link recycled,
        wait for reconnect and retry once.
        """
        try:
            await self._send_json({"method": "set", "params": params})
            return
        except Exception as first_exc:
            ok = await self.wait_connected(wait_reconnect)
            if not ok:
                raise RuntimeError(
                    f"printer link not available after {wait_reconnect}s"
                ) from first_exc
            await self._send_json({"method": "set", "params": params})

    async def _send_json(self, obj: dict[str, Any]) -> None:
        async with self._send_lock:
            ws = self._ws
            if not ws:
                raise RuntimeError("WebSocket not connected")
            await ws.send(json.dumps(obj, separators=(",", ":")))

    # ---------- health ----------
    def last_rx_monotonic(self) -> float:
        """Return the monotonic time of the last received message."""
        return self._last_rx
