"""Support for Orbit BHyve select entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory

from . import BHyveCoordinatorEntity
from .const import DEVICE_SPRINKLER, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BHyveDataUpdateCoordinator
    from .pybhyve.typings import BHyveDevice


@dataclass(frozen=True, kw_only=True)
class BHyveSelectEntityDescription(SelectEntityDescription):
    """Describes BHyve select entity."""

    unique_id_suffix: str
    name: str = ""
    device_types: tuple[str, ...] = ()


SELECT_TYPES: tuple[BHyveSelectEntityDescription, ...] = (
    BHyveSelectEntityDescription(
        key="device_mode",
        translation_key="device_mode",
        name="Device mode",
        icon="mdi:auto-mode",
        unique_id_suffix="device_mode",
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_SPRINKLER,),
        options=["auto", "off"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve select platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]

    entities = [
        BHyveSelectEntity(coordinator, device, description)
        for device in devices
        for description in SELECT_TYPES
        if device.get("type") in description.device_types
    ]

    async_add_entities(entities)


class BHyveSelectEntity(BHyveCoordinatorEntity, SelectEntity):
    """Define a BHyve select entity."""

    entity_description: BHyveSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        description: BHyveSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        self.entity_description = description
        self._attr_name = description.name
        super().__init__(coordinator, device)
        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{description.unique_id_suffix}"
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        status = self.device_data.get("status", {})
        return status.get("mode", status.get("run_mode"))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.client.send_message(
            {
                "event": "change_mode",
                "device_id": self._device_id,
                "mode": option,
            }
        )
