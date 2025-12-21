from __future__ import annotations

import asyncio
import json
import logging
import random
import socket
import time
from typing import Any, Awaitable, Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosed

from .const import (
    RETRY_MIN_BACKOFF,
    RETRY_MAX_BACKOFF,
    RETRY_BACKOFF_MULTIPLIER,
    HEARTBEAT_SECS,
    PROBE_ON_SILENCE_SECS,
    WS_URL_TEMPLATE,
)
from .utils import coerce_numbers

_LOGGER = logging.getLogger(__name__)
OnMessage = Callable[[dict[str, Any]], Awaitable[None]]

# Periodic “get” cadences (mirror browser behavior)
GET_REQPRINTERPARA_SEC = 5.0         # curPosition, autohome, etc.
GET_PRINT_OBJECTS_SEC = 2.0          # objects/exclusions/current object


## number coercion handled by utils.coerce_numbers


class KClient:
    """Resilient WS client with backoff, heartbeat 'ok', periodic GETs, and staleness tracking."""

    def __init__(self, host: str, on_message: OnMessage):
        self._host = host
        # Resolve host to IPv4 if available and build URL via template
        self._url = lambda: WS_URL_TEMPLATE.format(host=self._resolve_host())
        self._on_message = on_message
        self._check_power_status: Callable[[], bool] | None = None
        self._state: dict[str, Any] = {}

        self._task: Optional[asyncio.Task] = None
        self._ws: Optional[websockets.client.ClientConnection] = None  # type: ignore[attr-defined]
        self._stop = asyncio.Event()
        self._connected_once = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._last_rx = 0.0
        self._last_mdns_attempt = 0.0

        self._hb_task: Optional[asyncio.Task] = None
        self._tick_task: Optional[asyncio.Task] = None

        # NEW: event that indicates a live socket is present
        self._ws_ready = asyncio.Event()

    # ---------- lifecycle ----------
    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="K-ws-loop")

    async def stop(self) -> None:
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
        await self.stop()
        await self.start()

    # ---------- connectivity loop ----------
    def _resolve_host(self) -> str:
        try:
            return socket.gethostbyname(self._host)
        except Exception:
            return self._host

    async def _loop(self) -> None:
        backoff = RETRY_MIN_BACKOFF
        connect_failures = 0
        # Use faster backoff if power detection is disabled (allows quick retries when printer turns on)
        max_backoff = RETRY_MAX_BACKOFF if self._check_power_status else 30.0  # 30s max when no power detection
        
        while not self._stop.is_set():
            # --- Power Saving Check (Start of Loop) ---
            # If printer is known to be powered off, sleep and skip connection attempt
            if self._check_power_status and self._check_power_status():
                 _LOGGER.debug("Printer power is OFF; sleeping 60s before next check host=%s", self._host)
                 # Reset backoff so we start fresh when power returns
                 backoff = RETRY_MIN_BACKOFF
                 connect_failures = 0
                 try:
                     await asyncio.wait_for(self._stop.wait(), timeout=60.0)
                 except asyncio.TimeoutError:
                     pass
                 continue

            try:
                url = self._url()
                _LOGGER.debug("K WS connecting host=%s url=%s", self._host, url)
                # Disable library pings; we do app-level heartbeat + periodic GETs.
                async with websockets.connect(url, ping_interval=None) as ws:
                    self._ws = ws
                    self._ws_ready.set()  # signal connected
                    _LOGGER.info("K WS connected host=%s url=%s", self._host, url)
                    self._connected_once.set()
                    
                    # Store connect time to calculate duration later
                    connect_ts = time.monotonic()
                    self._last_rx = time.monotonic()
                    
                    # Reset failure counters on successful connection
                    connect_failures = 0
                    backoff = RETRY_MIN_BACKOFF

                    # background tasks
                    self._hb_task = asyncio.create_task(self._heartbeat(), name="K-ws-heartbeat")
                    self._tick_task = asyncio.create_task(self._periodic_gets(), name="K-ws-ticker")

                    async for raw in ws:
                        self._last_rx = time.monotonic()
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
                            # ACK immediately; literal 'ok' (no JSON)
                            try:
                                await ws.send("ok")
                            except Exception:
                                pass
                            continue

                        if isinstance(payload, dict):
                            merged = coerce_numbers(payload)
                            self._state.update(merged)
                            try:
                                await self._on_message(dict(self._state))
                            except Exception:
                                _LOGGER.exception("K on_message failed host=%s", self._host)
                        else:
                            _LOGGER.debug("K WS unexpected frame type: %r", type(payload))

            except asyncio.CancelledError:
                break
            except Exception as exc:
                connect_failures += 1
                
                # Check power status before logging loud errors.
                # If power is OFF, we treat it as expected (debug only).
                # But wait... we check power at TOP of loop.
                # This catch block is for when connect() fails or connection drops.
                # If it drops, it might be because user turned it off 1 second ago.
                is_off = self._check_power_status and self._check_power_status()
                
                if is_off:
                     _LOGGER.debug("K WS closed/failed (power OFF) host=%s reason=%s", self._host, exc)
                elif self._is_benign_close(exc):
                    _LOGGER.debug("K WS closed host=%s reason=%s", self._host, exc)
                else:
                    # Downgrade to WARNING for first few failures
                    if connect_failures <= 3:
                        _LOGGER.warning("K WS connection error host=%s err=%s (Failures=%d)", self._host, exc, connect_failures)
                    else:
                        # After 3 failures, only log every 5th time (or just DEBUG)
                        # We'll stick to debug to eliminate noise for long downtimes
                        _LOGGER.debug("K WS connection error host=%s err=%s (Failures=%d - suppressed)", self._host, exc, connect_failures)
            finally:
                # cleanup on disconnect
                for t in (self._hb_task, self._tick_task):
                    if t:
                        t.cancel()
                self._hb_task = self._tick_task = None

                self._ws = None
                self._ws_ready.clear()
                
                # We reset backoff inside the success block now, so no need for the
                # "reset if > 5s" logic here, which was flaky.
                pass

            # exponential backoff with jitter (use max_backoff based on power detection enabled)
            jitter = random.uniform(0.0, 0.4)
            sleep_for = min(backoff * (RETRY_BACKOFF_MULTIPLIER + jitter), max_backoff)
            
            # --- mDNS Recovery Logic ---
            # If we've hit max backoff, the IP might have changed. Try rediscovery.
            # Only if NOT powered off (which is handled above)
            # AND only if we haven't tried recently (prevent mDNS spam)
            if backoff >= (RETRY_MAX_BACKOFF * 0.9):
                now = time.monotonic()
                if now - self._last_mdns_attempt > 3.0: # 3 seconds
                    self._last_mdns_attempt = now
                    _LOGGER.warning("K WS connection failing repeatedly (host=%s). Attempting mDNS fallback...", self._host)
                    try:
                        from .config_flow import _probe_tcp # Delayed import
                        # Logic is handled by __init__.py Zeroconf listener, but we log explicitly here.
                        pass
                    except Exception as exc:
                        _LOGGER.debug("mDNS fallback attempt failed: %s", exc)
                else:
                    _LOGGER.debug("K WS connection failing, but mDNS fallback rate-limited host=%s", self._host)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass
            
            backoff = min(sleep_for, max_backoff)

        _LOGGER.debug("K WS loop exited host=%s", self._host)

    async def _reset_backoff_after_delay(self):
        """Wait 5 seconds after connection; if still connected, reset backoff."""
        try:
            await asyncio.sleep(5.0)
            if self._ws and not self._stop.is_set():
               # We can't easily access the local 'backoff' variable in _loop.
               # Instead, we rely on the fact that if we disconnect AFTER 5s, 
               # the next loop starts with existing backoff? 
               # Actually, the logic in _loop preserves 'backoff' across iterations.
               # To reset it, we need a way to signal or just let natural flow work?
               # Wait, if I removed `backoff = RETRY_MIN_BACKOFF` from the success block, 
               # it NEVER resets? That's bad.
               # Re-thinking: We want to resets backoff IF connection was successful for a while.
               # Since 'backoff' is local to _loop, I can't modify it from here.
               # I'll rely on a flag? Or move backoff to instance?
               # Simpler: In _loop, record connect time. On disconnect, if (now - connect_time) > 5s, reset backoff.
               pass
        except Exception:
            pass

    async def _heartbeat(self):
        """Benign probe on silent connects and a WS-level ping keeps NAT/state alive."""
        try:
            await asyncio.sleep(PROBE_ON_SILENCE_SECS)
            if self._stop.is_set():
                return
            if time.monotonic() - self._last_rx > PROBE_ON_SILENCE_SECS:
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
                try:
                    pong = await ws.ping()
                    await asyncio.wait_for(pong, timeout=5.0)
                except Exception:
                    _LOGGER.debug("K WS ping failed; forcing reconnect host=%s", self._host)
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
            t_para = 0.0
            t_objs = 0.0
            # Staggered loop to avoid bursts
            while True:
                now = time.monotonic()
                ws = self._ws
                if not ws:
                    break
                if self._stop.is_set():
                    break
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

                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            return

    # ---------- public send ----------
    async def send_set(self, **params: Any) -> None:
        """Single-attempt sender (kept for internal use)."""
        await self._send_json({"method": "set", "params": params})

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
        return self._last_rx
