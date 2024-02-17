import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform
from homeassistant.helpers import config_validation as cv
import logging
import voluptuous as vol
from .const import CONF_CHANNEL, CONF_CHANNEL_COUNT, CONF_PRESET, CONF_STEP
from .icsee_entity import ICSeeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "move",
        {
            vol.Required("cmd"): cv.string,
            vol.Optional("step"): cv.positive_int,
            vol.Optional("preset"): cv.positive_int,
            vol.Optional("channel"): cv.positive_int,
        },
        "async_move",
    )
    platform.async_register_entity_service(
        "synchronize_clock",
        {},
        "async_synchronize_clock",
    )
    platform.async_register_entity_service(
        "force_frame",
        {},
        "async_force_frame",
    )
    async_add_entities(
        [
            Alarm(hass, entry, channel)
            for channel in range(entry.data[CONF_CHANNEL_COUNT])
        ],
        update_before_add=False,
    )


class Alarm(ICSeeEntity, BinarySensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, channel: int = 0):
        super().__init__(hass, entry)
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self.channel = channel
        assert self._attr_unique_id  # set by ICSeeEntity
        self._attr_unique_id += f"_alarm_{self.channel}"
        if channel == 0:
            self._attr_name = "Motion Alarm"
        else:
            self._attr_name = f"Motion Alarm {channel}"
        self.cam.add_alarm_callback(self.onAlarm)

    def onAlarm(self, what, n):
        if what["Channel"] == self.channel:
            self._attr_is_on = what["Status"] == "Start"
            self._attr_extra_state_attributes = what
            self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        return self.cam.is_connected

    async def async_move(self, cmd: str, **kwargs):
        step = kwargs.get("step", self.entry.options.get(CONF_STEP, 2))
        preset = kwargs.get("preset", self.entry.options.get(CONF_PRESET, 0))
        channel = kwargs.get("channel", self.entry.options.get(CONF_CHANNEL, 0))
        if cmd == "Stop":
            await self.cam.dvrip.ptz("DirectionUp", preset=-1)
        else:
            await self.cam.dvrip.ptz(cmd, step=step, preset=preset, ch=channel)

    async def async_synchronize_clock(self):
        assert self.cam.dvrip
        await self.cam.dvrip.set_time()

    async def async_force_frame(self):
        def callback(*args):
            assert self.cam.dvrip
            self.cam.dvrip.stop_monitor()

        try:
            assert self.cam.dvrip
            await self.cam.dvrip.start_monitor(callback)
        except:
            pass

    async def async_will_remove_from_hass(self):
        super(ICSeeEntity)
        self.cam.remove_alarm_callback(self.onAlarm)
