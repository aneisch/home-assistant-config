"""Orbit BHyve websocket transport."""

import json
import logging
from asyncio import AbstractEventLoop, TimerHandle, ensure_future
from collections.abc import Callable
from math import ceil
from typing import Any

import aiohttp
from aiohttp import ClientWebSocketResponse, WSMsgType

from .const import WEB_HOST

_LOGGER = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPED = "stopped"

RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 300

HTTP_SERVER_ERROR_MIN = 500
HTTP_SERVER_ERROR_MAX = 600


# pylint: disable=too-many-instance-attributes
class OrbitWebsocket:
    """
    Websocket transport, session handling, message generation.

    Inspired by https://github.com/Kane610/deconz/blob/master/pydeconz/websocket.py.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        token: str,
        loop: AbstractEventLoop,
        session: aiohttp.ClientSession,
        url: str,
        async_callback: Callable,
    ) -> None:
        """Create resources for websocket communication."""
        self._token: str = token
        self._loop = loop
        self._session: aiohttp.ClientSession = session
        self._url: str = url
        self._async_callback: Callable = async_callback
        self._state: str = STATE_STOPPED

        self._heartbeat_cb = None
        self._heartbeat: int = 25
        self._ws: ClientWebSocketResponse | None = None
        self._closing: bool = False
        self._reconnect_delay: int = RECONNECT_DELAY
        # Keep the delayed retry handle so an integration unload can cancel it.
        self._reconnect_cb: TimerHandle | None = None

    def _cancel_heartbeat(self) -> None:
        if self._heartbeat_cb is not None:
            self._heartbeat_cb.cancel()
            self._heartbeat_cb = None

    def _cancel_reconnect(self) -> None:
        if self._reconnect_cb is not None:
            self._reconnect_cb.cancel()
            self._reconnect_cb = None

    def _reset_heartbeat(self) -> None:
        self._cancel_heartbeat()

        when = ceil(self._loop.time() + self._heartbeat)
        self._heartbeat_cb = self._loop.call_at(when, self._send_heartbeat)

    def _send_heartbeat(self) -> None:
        if self._ws is not None and not self._ws.closed:
            # fire-and-forget a task is not perfect but maybe ok for
            # sending ping. Otherwise we need a long-living heartbeat
            # task in the class.
            self._loop.create_task(self._ping())

    async def _ping(self) -> None:
        if self._ws is not None and not self._ws.closed:
            try:
                await self._ws.send_str(json.dumps({"event": "ping"}))
                self._reset_heartbeat()
            except ConnectionResetError:
                _LOGGER.debug("Connection reset while sending ping")
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Error sending ping: %s", err)

    @property
    def state(self) -> str:
        """Returns the state of the websocket."""
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        self._state = value

    def start(self) -> None:
        """Start the websocket."""
        self._cancel_reconnect()
        if self._closing:
            _LOGGER.info("Websocket closed intentionally, not starting")
            return

        if self.state != STATE_RUNNING:
            self.state = STATE_STARTING
        self._loop.create_task(self.running())

    async def running(self) -> None:  # noqa: PLR0912, PLR0915
        """Start websocket connection."""
        background_tasks = set()
        try:
            if self._ws is None or self._ws.closed or self.state != STATE_RUNNING:
                async with self._session.ws_connect(
                    self._url,
                    origin=WEB_HOST,
                    headers={"User-Agent": _USER_AGENT},
                ) as self._ws:
                    _LOGGER.info("Authenticating websocket")
                    await self._ws.send_str(
                        json.dumps(
                            {
                                "event": "app_connection",
                                "orbit_session_token": self._token,
                            }
                        )
                    )

                    _LOGGER.info("Websocket connected")

                    self._reset_heartbeat()
                    # The endpoint recovered; future disconnects should retry quickly.
                    self._reconnect_delay = RECONNECT_DELAY

                    self.state = STATE_RUNNING

                    while True:
                        if self.state == STATE_STOPPED:
                            _LOGGER.warning("Websocket is stopped, exiting loop")
                            break

                        msg = await self._ws.receive()
                        self._reset_heartbeat()

                        if msg.type == WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            log_data = data
                            if (
                                isinstance(data.get("program"), dict)
                                and "watering_plan" in data["program"]
                            ):
                                log_data = {
                                    **data,
                                    "program": {
                                        **data["program"],
                                        "watering_plan": "<removed>",
                                    },
                                }
                            _LOGGER.debug(
                                "msg received:\n%s", json.dumps(log_data, indent=2)
                            )
                            task = ensure_future(self._async_callback(data))
                            # Add task to the set to create a strong reference, and
                            # discard when finished so it can be garbage collected
                            background_tasks.add(task)
                            task.add_done_callback(background_tasks.discard)

                        elif msg.type == WSMsgType.PING:
                            await self._ws.pong()

                        elif msg.type == WSMsgType.CLOSE:
                            _LOGGER.debug("Websocket received CLOSE message, ignoring")
                            break

                        elif msg.type == WSMsgType.CLOSED:
                            _LOGGER.error("websocket connection closed")
                            break

                        elif msg.type == WSMsgType.ERROR:
                            _LOGGER.error(
                                "websocket error: %s", self._ws.exception() or "Unknown"
                            )
                            break

                    if self._ws.closed:
                        _LOGGER.info("Websocket closed? %s", self._ws.closed)
                        self._cancel_heartbeat()
                        self.state = STATE_STOPPED

                    if self._ws.exception():
                        _LOGGER.warning(
                            "Websocket exception: %s", self._ws.exception() or "Unknown"
                        )
                        self.state = STATE_STOPPED

        except aiohttp.ClientResponseError as err:
            if HTTP_SERVER_ERROR_MIN <= err.status < HTTP_SERVER_ERROR_MAX:
                _LOGGER.warning(
                    "Orbit websocket endpoint returned HTTP %s; retrying with backoff",
                    err.status,
                )
            else:
                _LOGGER.error("Unexpected websocket HTTP error %s", err)  # noqa: TRY400
            self.state = STATE_STOPPED
            self.retry()

        except aiohttp.ClientConnectorError:
            _LOGGER.warning("Client connection error; state: %s", self.state)
            self.state = STATE_STOPPED
            self.retry()

        # pylint: disable=broad-except
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected error %s", err)  # noqa: TRY400
            self.state = STATE_STOPPED
            self.retry()

        else:
            if self._closing:
                _LOGGER.info("Websocket closed intentionally, not reconnecting")
            else:
                _LOGGER.info("Reconnecting websocket; state: %s", self.state)
                self.retry()

    async def stop(self) -> None:
        """Close websocket connection."""
        _LOGGER.info("Closing websocket connection; state: %s --> STOPPED", self.state)
        self._closing = True
        self.state = STATE_STOPPED
        self._cancel_heartbeat()
        self._cancel_reconnect()
        if self._ws is not None:
            await self._ws.close()

    def retry(self) -> None:
        """Retry to connect to Orbit."""
        if self._closing:
            _LOGGER.info("Websocket closed intentionally, not scheduling reconnect")
            return

        if self.state != STATE_STARTING:
            _LOGGER.info(
                "Reconnecting to Orbit in %i; state: %s",
                self._reconnect_delay,
                self.state,
            )
            self.state = STATE_STARTING
            # Track the delayed start so stop() can prevent stale reconnects.
            self._reconnect_cb = self._loop.call_later(
                self._reconnect_delay, self.start
            )
            self._reconnect_delay = min(
                self._reconnect_delay * 2,
                MAX_RECONNECT_DELAY,
            )
        else:
            _LOGGER.info("Ignoring websocket retry; state: %s", self.state)

    async def send(self, payload: Any) -> None:
        """Send a websocket message."""
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_str(json.dumps(payload))
        else:
            _LOGGER.warning(
                "Tried to send message whilst websocket closed; state: %s", self.state
            )
