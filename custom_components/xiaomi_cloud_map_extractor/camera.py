import logging
from typing import Self

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONTENT_TYPE
from .coordinator import XiaomiCloudMapExtractorDataUpdateCoordinator
from .entity import XiaomiCloudMapExtractorEntity
from .types import XiaomiCloudMapExtractorConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: XiaomiCloudMapExtractorConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities([XiaomiCloudMapExtractorCamera(coordinator, config_entry)])


class XiaomiCloudMapExtractorCamera(XiaomiCloudMapExtractorEntity, Camera):

    def __init__(
            self: Self,
            coordinator: XiaomiCloudMapExtractorDataUpdateCoordinator,
            config_entry: XiaomiCloudMapExtractorConfigEntry
    ) -> None:
        XiaomiCloudMapExtractorEntity.__init__(self, coordinator, config_entry)
        Camera.__init__(self)
        self.content_type = CONTENT_TYPE

    @property
    def frame_interval(self: Self) -> float:
        return 0.2

    def camera_image(self: Self, width: int | None = None, height: int | None = None) -> bytes | None:
        data = self._data()
        if data is None:
            return None
        return data.map_image

    @property
    def name(self: Self) -> str:
        return "Live Map"
