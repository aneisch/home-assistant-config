"""Define an object to interact with the REST API."""

import asyncio
import logging
import re
import time
from asyncio import AbstractEventLoop, ensure_future
from collections.abc import Callable
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from .const import (
    API_HOST,
    API_POLL_PERIOD,
    DEVICE_HISTORY_PATH,
    DEVICES_PATH,
    LANDSCAPE_DESCRIPTIONS_PATH,
    LOGIN_PATH,
    TIMER_PROGRAMS_PATH,
    WEB_HOST,
    WS_HOST,
)
from .errors import AuthenticationError, BHyveError, RequestError
from .typings import BHyveDevice, BHyveTimerProgram, BHyveZoneLandscape
from .websocket import OrbitWebsocket

_LOGGER = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


class BHyveClient:
    """Define the API object."""

    def __init__(self, username: str, password: str, session: ClientSession) -> None:
        """Initialize."""
        self._username: str = username
        self._password: str = password
        self._ws_url: str = WS_HOST
        self._token: str | None = None

        self._websocket: OrbitWebsocket | None = None
        self._session = session

        self._devices: list[BHyveDevice] = []
        self._last_poll_devices = 0

        self._timer_programs: list[BHyveTimerProgram] = []
        self._last_poll_programs = 0

        self._device_histories: dict[str, Any] = {}
        self._last_poll_device_histories: dict[str, float] = {}

        self._landscapes: dict[str, list[BHyveZoneLandscape]] = {}
        self._last_poll_landscapes: dict[str, float] = {}
        self._landscape_locks: dict[str, asyncio.Lock] = {}

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> list:
        """Make a request against the API."""
        url: str = f"{API_HOST}{endpoint}"

        if not params:
            params = {}

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Host": re.sub("https?://", "", API_HOST),
            "Content-Type": "application/json; charset=utf-8;",
            "Origin": WEB_HOST,
            "Referer": f"{WEB_HOST}/",
            "User-Agent": _USER_AGENT,
            "orbit-app-id": "Bhyve Dashboard",
            "orbit-api-key": self._token or "null",
            "Orbit-Session-Token": self._token or "",
        }

        try:
            async with self._session.request(
                method, url, params=params, headers=headers, json=json
            ) as resp:
                try:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
                except ClientResponseError as err:
                    if err.status in (401, 403):
                        _LOGGER.warning(
                            "Authentication error from %s: %s", url, err.status
                        )
                        raise AuthenticationError from err
                    msg = f"Error requesting data from {url}: {err}"
                    raise RequestError(msg) from err
                except Exception as err:
                    msg = f"Error requesting data from {url}: {err}"
                    raise RequestError(msg) from err
        except TimeoutError as err:
            msg = f"Timeout requesting data from {url}"
            raise RequestError(msg) from err

    async def _refresh_devices(self, *, force_update: bool = False) -> None:
        now = time.time()
        if force_update:
            _LOGGER.info("Forcing device refresh")
        elif now - self._last_poll_devices < API_POLL_PERIOD:
            return

        self._devices: list[BHyveDevice] = await self._request(
            "get", DEVICES_PATH, params={"t": str(time.time())}
        )

        self._last_poll_devices = now

    async def _refresh_timer_programs(self, *, force_update: bool = False) -> None:
        now = time.time()
        if force_update:
            _LOGGER.debug("Forcing device refresh")
        elif now - self._last_poll_programs < API_POLL_PERIOD:
            return

        self._timer_programs: list[BHyveTimerProgram] = await self._request(
            "get", TIMER_PROGRAMS_PATH, params={"t": str(time.time())}
        )
        self._last_poll_programs = now

    async def _refresh_device_history(
        self, device_id: str, *, force_update: bool = False
    ) -> None:
        now = time.time()
        if force_update:
            _LOGGER.info("Forcing refresh of device history %s", device_id)
        elif now - self._last_poll_device_histories.get(device_id, 0) < API_POLL_PERIOD:
            return

        device_history = await self._request(
            "get",
            DEVICE_HISTORY_PATH.format(device_id),
            params={
                "t": str(time.time()),
                "page": str(1),
                "per-page": str(10),
            },
        )

        self._device_histories.update({device_id: device_history})

        self._last_poll_device_histories[device_id] = now

    async def _refresh_landscapes(
        self, device_id: str, *, force_update: bool = False
    ) -> None:
        # Single-flight: concurrent callers for the same device share one HTTP
        # request. Without this, a coordinator refresh that fans out per-zone
        # landscape lookups for N zones fires N duplicate requests.
        lock = self._landscape_locks.get(device_id)
        if lock is None:
            lock = asyncio.Lock()
            self._landscape_locks[device_id] = lock

        async with lock:
            now = time.time()
            if force_update:
                _LOGGER.debug("Forcing landscape refresh %s", device_id)
            elif now - self._last_poll_landscapes.get(device_id, 0) < API_POLL_PERIOD:
                return

            device_landscapes = await self._request(
                "get",
                f"{LANDSCAPE_DESCRIPTIONS_PATH}/{device_id}",
                params={"t": str(time.time())},
            )

            self._landscapes[device_id] = device_landscapes or []
            self._last_poll_landscapes[device_id] = now

    async def _async_ws_handler(self, async_callback: Callable, data: Any) -> None:
        """Process incoming websocket message."""
        ensure_future(async_callback(data))  # noqa: RUF006

    async def login(self) -> bool:
        """Log in with username & password and save the token."""
        url: str = f"{API_HOST}{LOGIN_PATH}"
        json = {"session": {"email": self._username, "password": self._password}}
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=UTF-8",
            "Origin": WEB_HOST,
            "Referer": f"{WEB_HOST}/",
            "User-Agent": _USER_AGENT,
            "orbit-app-id": "Bhyve Dashboard",
            "orbit-api-key": "null",
        }

        try:
            async with self._session.request(
                "post", url, json=json, headers=headers
            ) as resp:
                try:
                    resp.raise_for_status()
                    response = await resp.json(content_type=None)
                    self._token = response["orbit_api_key"]

                except ClientResponseError as response_err:
                    if response_err.status in (401, 403):
                        raise AuthenticationError from response_err
                    raise RequestError from response_err
                except Exception as err:
                    msg = f"Error requesting data from {url}: {err}"
                    raise RequestError(msg) from err
        except TimeoutError as err:
            msg = f"Timeout requesting data from {url}"
            raise RequestError(msg) from err

        return self._token is not None

    def listen(self, loop: AbstractEventLoop, async_callback: Callable) -> None:
        """Start listening to the Orbit event stream."""
        if self._token is None:
            msg = "Client is not logged in"
            raise BHyveError(msg)

        self._websocket = OrbitWebsocket(
            token=self._token,
            loop=loop,
            session=self._session,
            url=self._ws_url,
            async_callback=async_callback,
        )
        self._websocket.start()

    async def stop(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, ARG002
        """Stop the websocket."""
        if self._websocket is not None:
            await self._websocket.stop()

    @property
    async def devices(self) -> list[BHyveDevice]:
        """Get all devices."""
        await self._refresh_devices()
        return self._devices

    @property
    async def timer_programs(self) -> list[BHyveTimerProgram]:
        """Get timer programs."""
        await self._refresh_timer_programs()
        return self._timer_programs

    async def get_device(
        self, device_id: str, *, force_update: bool = False
    ) -> BHyveDevice | None:
        """Get device by id."""
        await self._refresh_devices(force_update=force_update)
        for device in self._devices:
            if device.get("id") == device_id:
                return device
        return None

    async def get_device_history(
        self, device_id: str, *, force_update: bool = False
    ) -> dict | None:
        """Get device watering history by id."""
        await self._refresh_device_history(device_id, force_update=force_update)
        return self._device_histories.get(device_id)

    async def get_landscape(
        self, device_id: str, zone_id: str, *, force_update: bool = False
    ) -> BHyveZoneLandscape | None:
        """Get landscape by zone id."""
        await self._refresh_landscapes(device_id, force_update=force_update)
        for zone in self._landscapes.get(device_id, []):
            if zone.get("station") == zone_id:
                return zone
        return None

    async def update_landscape(self, landscape: BHyveZoneLandscape) -> None:
        """Update the state of a zone landscape."""
        landscape_id = landscape.get("id")
        path = f"{LANDSCAPE_DESCRIPTIONS_PATH}/{landscape_id}"
        json = {"landscape_description": landscape}
        await self._request("put", path, json=json)

    async def update_program(self, program_id: str, program: BHyveTimerProgram) -> None:
        """Update the state of a program."""
        path = f"{TIMER_PROGRAMS_PATH}/{program_id}"
        json = {"sprinkler_timer_program": program}
        await self._request("put", path, json=json)

    async def update_device(self, device: dict) -> None:
        """Update device settings."""
        device_id = device.get("id")
        path = f"{DEVICES_PATH}/{device_id}"
        json = {"device": device}
        await self._request("put", path, json=json)

    async def send_message(self, payload: Any) -> None:
        """Send a message via the websocket."""
        if self._websocket is not None:
            await self._websocket.send(payload)

    async def set_rain_delay(self, device_id: str, hours: int) -> None:
        """Set rain delay hours for a device. Use hours=0 to disable."""
        payload = {
            "event": "rain_delay",
            "device_id": device_id,
            "delay": hours,
        }
        _LOGGER.info("Setting rain delay: %s", payload)
        await self.send_message(payload)

    async def set_manual_preset_runtime(self, device_id: str, minutes: int) -> None:
        """Set the default watering runtime for a device."""
        payload = {
            "event": "set_manual_preset_runtime",
            "device_id": device_id,
            "seconds": minutes * 60,
        }
        _LOGGER.info("Setting manual preset runtime: %s", payload)
        await self.send_message(payload)
