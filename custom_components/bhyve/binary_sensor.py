"""Support for Orbit BHyve binary sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from . import BHyveCoordinatorEntity
from .const import DEVICE_BRIDGE, DEVICE_FLOOD, DEVICE_SPRINKLER, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BHyveDataUpdateCoordinator
    from .pybhyve.typings import BHyveDevice


@dataclass(frozen=True, kw_only=True)
class BHyveBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes BHyve binary sensor entity."""

    unique_id_suffix: str
    name: str = ""
    # Device types this sensor applies to (e.g., DEVICE_FLOOD, DEVICE_SPRINKLER)
    device_types: tuple[str, ...] = ()
    # Callable that takes device_data and returns bool
    value_fn: Any = None
    # Callable that takes device_data and returns attributes
    attributes_fn: Any = None


BINARY_SENSOR_TYPES: tuple[BHyveBinarySensorEntityDescription, ...] = (
    BHyveBinarySensorEntityDescription(
        key="flood",
        translation_key="flood",
        name="Flood sensor",
        device_class=BinarySensorDeviceClass.MOISTURE,
        unique_id_suffix="water",
        device_types=(DEVICE_FLOOD,),
        value_fn=lambda data: (
            data.get("status", {}).get("flood_alarm_status") == "alarm"
        ),
        attributes_fn=lambda data: {
            "location": data.get("location_name"),
            "auto_shutoff": data.get("auto_shutoff"),
        },
    ),
    BHyveBinarySensorEntityDescription(
        key="temperature_alert",
        translation_key="temperature_alert",
        name="Temperature alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        unique_id_suffix="tempalert",
        device_types=(DEVICE_FLOOD,),
        value_fn=lambda data: (
            "alarm" in data.get("status", {}).get("temp_alarm_status", "")
        ),
        attributes_fn=lambda data: {
            **(
                thresh
                if isinstance(thresh := data.get("temp_alarm_thresholds"), dict)
                else {}
            ),
            "problem_type": "temperature",
        },
    ),
    BHyveBinarySensorEntityDescription(
        key="fault",
        translation_key="fault",
        name="Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        unique_id_suffix="fault",
        device_types=(DEVICE_SPRINKLER,),
        value_fn=lambda data: bool(data.get("status", {}).get("station_faults")),
        attributes_fn=lambda data: {
            "station_faults": data.get("status", {}).get("station_faults", []),
        },
    ),
    BHyveBinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        name="Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        unique_id_suffix="connectivity",
        device_types=(DEVICE_BRIDGE,),
        value_fn=lambda data: data.get("is_connected", False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve binary sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]

    entities = [
        BHyveBinarySensor(coordinator, device, description)
        for device in devices
        for description in BINARY_SENSOR_TYPES
        if device.get("type") in description.device_types
    ]

    async_add_entities(entities)


class BHyveBinarySensor(BHyveCoordinatorEntity, BinarySensorEntity):
    """Define a BHyve binary sensor."""

    entity_description: BHyveBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        description: BHyveBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._attr_name = description.name
        super().__init__(coordinator, device)
        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{description.unique_id_suffix}"
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.device_data)
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.device_data)
        return {}
