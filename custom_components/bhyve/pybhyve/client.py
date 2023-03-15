"""Define an object to interact with the REST API."""

from asyncio import ensure_future
import logging
import re
import time
from typing import Any

from aiohttp import ClientResponseError

from .const import (
    API_HOST,
    API_POLL_PERIOD,
    DEVICE_HISTORY_PATH,
    DEVICES_PATH,
    LANDSCAPE_DESCRIPTIONS_PATH,
    LOGIN_PATH,
    TIMER_PROGRAMS_PATH,
    WS_HOST,
)
from .errors import AuthenticationError, BHyveError, RequestError
from .websocket import OrbitWebsocket

_LOGGER = logging.getLogger(__name__)


class Client:
    """Define the API object."""

    def __init__(self, username: str, password: str, session) -> None:
        """Initialize."""
        self._username: str = username
        self._password: str = password
        self._ws_url: str = WS_HOST
        self._token: str = None

        self._websocket = None
        self._session = session

        self._devices = list[Any]
        self._last_poll_devices = 0

        self._timer_programs = list[Any]
        self._last_poll_programs = 0

        self._device_histories = {}
        self._last_poll_device_histories = 0

        self._landscapes = list[Any]
        self._last_poll_landscapes = 0

    async def _request(
        self, method: str, endpoint: str, params: dict = None, json: dict = None
    ) -> list:
        """Make a request against the API."""
        url: str = f"{API_HOST}{endpoint}"

        if not params:
            params = {}

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Host": re.sub("https?://", "", API_HOST),
            "Content-Type": "application/json; charset=utf-8;",
            "Referer": API_HOST,
            "Orbit-Session-Token": self._token or "",
        }
        headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/72.0.3626.81 Safari/537.36"
        )

        async with self._session.request(
            method, url, params=params, headers=headers, json=json
        ) as resp:
            try:
                resp.raise_for_status()
                return await resp.json(content_type=None)
            except Exception as err:
                raise RequestError(f"Error requesting data from {url}: {err}") from err

    async def _refresh_devices(self, force_update=False):
        now = time.time()
        if force_update:
            _LOGGER.info("Forcing device refresh")
        elif now - self._last_poll_devices < API_POLL_PERIOD:
            return

        self._devices = await self._request(
            "get", DEVICES_PATH, params={"t": str(time.time())}
        )

        self._last_poll_devices = now

    async def _refresh_timer_programs(self, force_update=False):
        now = time.time()
        if force_update:
            _LOGGER.debug("Forcing device refresh")
        elif now - self._last_poll_programs < API_POLL_PERIOD:
            return

        self._timer_programs = await self._request(
            "get", TIMER_PROGRAMS_PATH, params={"t": str(time.time())}
        )
        self._last_poll_programs = now

    async def _refresh_device_history(self, device_id, force_update=False):
        now = time.time()
        if force_update:
            _LOGGER.info("Forcing refresh of device history %s", device_id)
        elif now - self._last_poll_device_histories < API_POLL_PERIOD:
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

        self._last_poll_device_histories = now

    async def _refresh_landscapes(self, device_id, force_update=False):
        now = time.time()
        if force_update:
            _LOGGER.debug("Forcing landscape refresh %s", device_id)
        elif now - self._last_poll_landscapes < API_POLL_PERIOD:
            return

        self._landscapes = await self._request(
            "get",
            f"{LANDSCAPE_DESCRIPTIONS_PATH}/{device_id}",
            params={"t": str(time.time())},
        )

        self._last_poll_landscapes = now

    async def _async_ws_handler(self, async_callback, data):
        """Process incoming websocket message."""
        ensure_future(async_callback(data))

    async def login(self) -> bool:
        """Log in with username & password and save the token."""
        url: str = f"{API_HOST}{LOGIN_PATH}"
        json = {"session": {"email": self._username, "password": self._password}}

        async with self._session.request("post", url, json=json) as resp:
            try:
                resp.raise_for_status()
                response = await resp.json(content_type=None)
                _LOGGER.debug("Logged in")
                self._token = response["orbit_session_token"]

            except ClientResponseError as response_err:
                if response_err.status == 400:
                    raise AuthenticationError from response_err
                raise RequestError from response_err
            except Exception as err:
                raise RequestError(f"Error requesting data from {url}: {err}") from err

        if self._token is None:
            return False

        return True

    def listen(self, loop, async_callback):
        """Starts listening to the Orbit event stream."""
        if self._token is None:
            raise BHyveError("Client is not logged in")

        self._websocket = OrbitWebsocket(
            token=self._token,
            loop=loop,
            session=self._session,
            url=self._ws_url,
            async_callback=async_callback,
        )
        self._websocket.start()

    async def stop(self):
        """Stop the websocket."""
        if self._websocket is not None:
            await self._websocket.stop()

    @property
    async def devices(self):
        """Get all devices."""
        await self._refresh_devices()
        return self._devices

    @property
    async def timer_programs(self):
        """Get timer programs."""
        await self._refresh_timer_programs()
        return self._timer_programs

    async def get_device(self, device_id, force_update=False):
        """Get device by id."""
        await self._refresh_devices(force_update=force_update)
        for device in self._devices:
            if device.get("id") == device_id:
                return device
        return None

    async def get_device_history(self, device_id, force_update=False):
        """Get device watering history by id."""
        await self._refresh_device_history(device_id, force_update=force_update)
        return self._device_histories.get(device_id)

    async def get_landscape(self, device_id, zone_id, force_update=False):
        """Get landscape by zone id."""
        await self._refresh_landscapes(device_id, force_update)
        for zone in self._landscapes:
            if zone.get("station") == zone_id:
                return zone
        return None

    async def update_landscape(self, landscape):
        """Update the state of a zone landscape."""
        landscape_id = landscape.get("id")
        path = f"{LANDSCAPE_DESCRIPTIONS_PATH}/{landscape_id}"
        json = {"landscape_description": landscape}
        await self._request("put", path, json=json)

    async def update_program(self, program_id, program):
        """Update the state of a program."""
        path = f"{TIMER_PROGRAMS_PATH}/{program_id}"
        json = {"sprinkler_timer_program": program}
        await self._request("put", path, json=json)

    async def send_message(self, payload):
        """Send a message via the websocket."""
        await self._websocket.send(payload)
