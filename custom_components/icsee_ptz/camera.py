import asyncio

from homeassistant.core import HomeAssistant
from .asyncio_dvrip import DVRIPCam, SomethingIsWrongWithCamera


class Camera:
    def __init__(
        self, hass: HomeAssistant, host: str, user: str, password: str
    ) -> None:
        """DVRIp wrapper that handles reconnects."""
        self.hass = hass
        self.host = host
        self.user = user
        self.password = password
        self.dvrip = None
        self.dvrip_alarm = None
        self.alarm_callbacks = []
        self.update_callbacks = []
        self.system_info: dict = {}
        self.detect_info: dict = {}
        self.camara_info: dict = {}
        self._last_connection_success = False

    def on_update(self, callback):
        self.update_callbacks.append(callback)

    def remove_on_update(self, callback):
        self.update_callbacks.remove(callback)

    def add_alarm_callback(self, callback):
        self.alarm_callbacks.append(callback)

    def remove_alarm_callback(self, callback):
        self.alarm_callbacks.remove(callback)

    def on_alarm(self, what, n):
        for cb in self.alarm_callbacks:
            cb(what, n)

    @property
    def is_connected(self) -> bool:
        return bool(self._last_connection_success and self.dvrip_alarm and self.dvrip_alarm.socket_reader)

    async def async_ensure_alive(self):
        # Keepalive is currently broken in python-dvr (see https://github.com/NeiroNx/python-dvr/issues/48),
        # so I'm instead logging in again on every update.
        # To ensure no messages are lost, a new connection is established before dropping the previous one.
        while True:
            dvrip = DVRIPCam(
                self.host,
                user=self.user,
                password=self.password,
            )
            dvrip_alarm = DVRIPCam(
                self.host,
                user=self.user,
                password=self.password,
            )
            try:
                await dvrip.login(self.hass.loop)
                await dvrip_alarm.login(self.hass.loop)
                dvrip_alarm.setAlarm(self.on_alarm)
                await dvrip_alarm.alarmStart(self.hass.loop)
                if not self.detect_info:
                    self.system_info = await dvrip.get_system_info()  # type: ignore
                    self.detect_info = await dvrip.get_info("Detect")  # type: ignore
                    self.camara_info = await dvrip.get_info("Camera")  # type: ignore

                dvrip, self.dvrip = self.dvrip, dvrip
                dvrip_alarm, self.dvrip_alarm = self.dvrip_alarm, dvrip_alarm

                if dvrip:
                    dvrip.close()
                if dvrip_alarm:
                    dvrip_alarm.close()

                if not self._last_connection_success:
                    await self.dvrip.set_time()
                    self._last_connection_success = True
            except SomethingIsWrongWithCamera:
                self._last_connection_success = False
                pass
            except asyncio.CancelledError:
                self._last_connection_success = False
                if dvrip:
                    dvrip.close()
                if dvrip_alarm:
                    dvrip_alarm.close()
                if self.dvrip:
                    self.dvrip.close()
                if self.dvrip_alarm:
                    self.dvrip_alarm.close()
                raise

            for cb in self.update_callbacks:
                try:
                    cb()  # if it fails nowm it isn't loaded yet.
                except:
                    pass

            await asyncio.sleep(20)
