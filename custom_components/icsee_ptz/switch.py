import logging
from homeassistant.components.switch import SwitchEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging
from .icsee_entity import ICSeeEntity

from .const import (
    CONF_CHANNEL_COUNT,
    CONF_EXPERIMENTAL_ENTITIES,
    CONF_SYSTEM_CAPABILITIES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    new_entities = []
    if not entry.options.get(CONF_EXPERIMENTAL_ENTITIES):
        return
    caps = entry.data[CONF_SYSTEM_CAPABILITIES]["AlarmFunction"]
    for channel in range(entry.data[CONF_CHANNEL_COUNT]):
        if caps.get("MotionDetect"):
            new_entities.append(AlarmSwitch(hass, entry, "MotionDetect", channel))
        if caps.get("HumanDection"):
            # yes. "dection" instead of "detection" in AlarmFunction, but "HumanDetection" in alarm type
            new_entities.append(AlarmSwitch(hass, entry, "HumanDetection", channel))
        if caps.get("BlindDetect"):
            new_entities.append(AlarmSwitch(hass, entry, "BlindDetect", channel))
        if caps.get("CarShapeDetection"):
            new_entities.append(AlarmSwitch(hass, entry, "CarShapeDetection", channel))
        if caps.get("LossDetect"):
            new_entities.append(AlarmSwitch(hass, entry, "LossDetect", channel))

    async_add_entities(
        new_entities,
        update_before_add=False,
    )


class AlarmSwitch(ICSeeEntity, SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        detect_type: str,
        channel: int = 0,
    ):
        super().__init__(hass, entry)
        self.channel = channel
        self.detect_type = detect_type
        self._attr_icon = "mdi:motion"
        assert self._attr_unique_id  # set by ICSeeEntity
        self._attr_unique_id += f"_{detect_type}_{channel}"

        if channel == 0:
            self._attr_name = f"{detect_type} Enabled"
        else:
            self._attr_name = f"{detect_type} Enabled {channel}"
        self._attr_extra_state_attributes = entry.data[CONF_SYSTEM_CAPABILITIES]

    @property
    def is_on(self, **kwargs):
        return self.cam.detect_info[self.detect_type][self.channel]["Enable"]

    async def async_turn_on(self, **kwargs):
        x = await self.cam.dvrip.get_info("Detect")
        x[self.detect_type][self.channel]["Enable"] = True
        await self.cam.dvrip.set_info("Detect", x)
        self.cam.detect_info = x

    async def async_turn_off(self, **kwargs):
        x = await self.cam.dvrip.get_info("Detect")
        x[self.detect_type][self.channel]["Enable"] = False
        await self.cam.dvrip.set_info("Detect", x)
        self.cam.detect_info = x
