"""Support for Orbit BHyve sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.helpers.icon import icon_for_battery_level

from . import BHyveCoordinatorEntity
from .const import (
    DEVICE_FLOOD,
    DEVICE_SPRINKLER,
    DOMAIN,
)
from .util import orbit_time_to_local_time

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BHyveDataUpdateCoordinator
    from .pybhyve.typings import BHyveDevice

_LOGGER = logging.getLogger(__name__)

ATTR_BUDGET = "budget"
ATTR_CONSUMPTION_GALLONS = "consumption_gallons"
ATTR_CONSUMPTION_LITRES = "consumption_litres"
ATTR_IRRIGATION = "irrigation"
ATTR_PROGRAM = "program"
ATTR_PROGRAM_NAME = "program_name"
ATTR_RUN_TIME = "run_time"
ATTR_NEXT_START_PROGRAMS = "programs"
ATTR_START_TIME = "start_time"
ATTR_STATUS = "status"


def _parse_battery_level(battery_data: dict) -> int:
    """
    Parse battery level data and return as percentage.

    If the 'percent' attribute is present in the battery data, it is used.
    Otherwise, if the 'mv' attribute is present, the battery level is
    calculated as a percentage based on millivolts, assuming 2x1.5V AA
    batteries. Note that AA batteries can range from 1.2V to 1.7V depending
    on their chemistry, so the calculation may not be accurate for all types.

    Args:
    ----
    battery_data (dict): A dictionary containing the battery data.

    Returns:
    -------
    int: The battery level as a percentage.

    """
    if not isinstance(battery_data, dict):
        _LOGGER.warning("Unexpected battery data, returning 0: %s", battery_data)
        return 0

    battery_level = battery_data.get("percent", 0)
    if "mv" in battery_data and "percent" not in battery_data:
        battery_level = min(battery_data.get("mv", 0) / 3000 * 100, 100)
    return int(battery_level)


@dataclass(frozen=True, kw_only=True)
class BHyveSensorEntityDescription(SensorEntityDescription):
    """Describes BHyve sensor entity."""

    unique_id_suffix: str
    name: str = ""
    # Callable that takes device_data and returns value
    value_fn: Any = None
    # Callable that takes device_data and returns attributes
    attributes_fn: Any = None
    # Callable that takes device_data and native_value, returns icon
    icon_fn: Any = None
    # Callable that takes device_data and native_value, returns bool
    available_fn: Any = None


SENSOR_TYPES_SPRINKLER: tuple[BHyveSensorEntityDescription, ...] = (
    BHyveSensorEntityDescription(
        key="state",
        translation_key="state",
        name="State",
        icon="mdi:information",
        unique_id_suffix="state",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status", {}).get("run_mode", "unavailable"),
    ),
    BHyveSensorEntityDescription(
        key="next_watering",
        translation_key="next_watering",
        name="Next watering",
        unique_id_suffix="next_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:sprinkler-variant",
        value_fn=lambda data: orbit_time_to_local_time(
            data.get("status", {}).get("next_start_time")
        ),
        attributes_fn=lambda data: (
            {ATTR_NEXT_START_PROGRAMS: programs}
            if (programs := data.get("status", {}).get("next_start_programs"))
            else {}
        ),
    ),
)

SENSOR_TYPES_FLOOD: tuple[BHyveSensorEntityDescription, ...] = (
    BHyveSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        name="Temperature sensor",
        icon="mdi:thermometer",
        unique_id_suffix="temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data: (
            float(temp)
            if (temp := data.get("status", {}).get("temp_f")) is not None
            else None
        ),
        attributes_fn=lambda data: {
            "location": data.get("location_name"),
        },
        available_fn=lambda _data, value: value is not None,
    ),
    BHyveSensorEntityDescription(
        key="rssi",
        translation_key="signal_strength",
        name="Signal strength",
        unique_id_suffix="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("status", {}).get("rssi"),
    ),
)

SENSOR_TYPES_BATTERY: tuple[BHyveSensorEntityDescription, ...] = (
    BHyveSensorEntityDescription(
        key="battery",
        translation_key="battery",
        name="Battery level",
        icon="mdi:battery",
        unique_id_suffix="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            _parse_battery_level(battery) if (battery := data.get("battery")) else None
        ),
        attributes_fn=lambda data: (
            {ATTR_BATTERY_LEVEL: level}
            if (battery := data.get("battery"))
            and (level := _parse_battery_level(battery))
            else {}
        ),
        icon_fn=lambda _data, value: (
            icon_for_battery_level(battery_level=int(value), charging=False)
            if value is not None
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the BHyve sensor platform from a config entry."""
    coordinator: BHyveDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    devices: list[BHyveDevice] = hass.data[DOMAIN][entry.entry_id]["devices"]

    sensors = []

    for device in devices:
        if device.get("type") == DEVICE_SPRINKLER:
            # Add state sensors
            for base_description in SENSOR_TYPES_SPRINKLER:
                description = BHyveSensorEntityDescription(
                    key=base_description.key,
                    translation_key=base_description.translation_key,
                    name=base_description.name,
                    icon=base_description.icon,
                    unique_id_suffix=base_description.unique_id_suffix,
                    device_class=base_description.device_class,
                    entity_category=base_description.entity_category,
                    value_fn=base_description.value_fn,
                    attributes_fn=base_description.attributes_fn,
                    icon_fn=base_description.icon_fn,
                    available_fn=base_description.available_fn,
                )
                sensors.append(BHyveSensor(coordinator, device, description))

            # Add zone history sensors
            all_zones = device.get("zones", [])
            for zone in all_zones:
                # if the zone doesn't have a name, set it to the device's name if
                # there is only one (eg a hose timer)
                zone_name: str = zone.get("name") or (
                    device.get("name", "Unnamed Zone")
                    if len(all_zones) == 1
                    else "Unnamed Zone"
                )
                sensors.append(
                    BHyveZoneHistorySensor(
                        coordinator,
                        device,
                        zone,
                        zone_name,
                        SensorEntityDescription(
                            key="zone_history",
                            translation_key="zone_history",
                            icon="mdi:history",
                            device_class=SensorDeviceClass.TIMESTAMP,
                            entity_category=EntityCategory.DIAGNOSTIC,
                        ),
                    )
                )

            # Add battery sensor if device has battery
            if device.get("battery", None) is not None:
                for base_description in SENSOR_TYPES_BATTERY:
                    description = BHyveSensorEntityDescription(
                        key=base_description.key,
                        translation_key=base_description.translation_key,
                        name=base_description.name,
                        icon=base_description.icon,
                        unique_id_suffix=base_description.unique_id_suffix,
                        device_class=base_description.device_class,
                        state_class=base_description.state_class,
                        native_unit_of_measurement=base_description.native_unit_of_measurement,
                        entity_category=base_description.entity_category,
                        value_fn=base_description.value_fn,
                        attributes_fn=base_description.attributes_fn,
                        icon_fn=base_description.icon_fn,
                        available_fn=base_description.available_fn,
                    )
                    sensors.append(BHyveSensor(coordinator, device, description))

        if device.get("type") == DEVICE_FLOOD:
            # Add temperature and RSSI sensors
            for base_description in SENSOR_TYPES_FLOOD:
                description = BHyveSensorEntityDescription(
                    key=base_description.key,
                    translation_key=base_description.translation_key,
                    name=base_description.name,
                    icon=base_description.icon,
                    unique_id_suffix=base_description.unique_id_suffix,
                    device_class=base_description.device_class,
                    state_class=base_description.state_class,
                    native_unit_of_measurement=base_description.native_unit_of_measurement,
                    entity_category=base_description.entity_category,
                    value_fn=base_description.value_fn,
                    attributes_fn=base_description.attributes_fn,
                    icon_fn=base_description.icon_fn,
                    available_fn=base_description.available_fn,
                )
                sensors.append(BHyveSensor(coordinator, device, description))

            # Add battery sensor
            for base_description in SENSOR_TYPES_BATTERY:
                description = BHyveSensorEntityDescription(
                    key=base_description.key,
                    translation_key=base_description.translation_key,
                    name=base_description.name,
                    icon=base_description.icon,
                    unique_id_suffix=base_description.unique_id_suffix,
                    device_class=base_description.device_class,
                    state_class=base_description.state_class,
                    native_unit_of_measurement=base_description.native_unit_of_measurement,
                    entity_category=base_description.entity_category,
                    value_fn=base_description.value_fn,
                    attributes_fn=base_description.attributes_fn,
                    icon_fn=base_description.icon_fn,
                    available_fn=base_description.available_fn,
                )
                sensors.append(BHyveSensor(coordinator, device, description))

    async_add_entities(sensors)


class BHyveSensor(BHyveCoordinatorEntity, SensorEntity):
    """Define a BHyve sensor."""

    entity_description: BHyveSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        description: BHyveSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._attr_name = description.name
        super().__init__(coordinator, device)
        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{description.unique_id_suffix}"
        )

    @property
    def native_value(self) -> datetime | int | float | str | None:
        """Return the state of the entity."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.device_data)
        return None

    @property
    def icon(self) -> str | None:
        """Icon to use in the frontend, if any."""
        if self.entity_description.icon_fn:
            return self.entity_description.icon_fn(self.device_data, self.native_value)
        return super().icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        if self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.device_data)
        return {}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity_description.available_fn:
            return super().available and self.entity_description.available_fn(
                self.device_data, self.native_value
            )
        return super().available


class BHyveZoneHistorySensor(BHyveCoordinatorEntity, SensorEntity):
    """Define a BHyve zone history sensor."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
        zone: dict,
        zone_name: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        if zone_name == device.get("name"):
            self._attr_name = "Zone history"
        else:
            self._attr_name = f"{zone_name} zone history"
        self._attr_translation_placeholders = {"zone_name": zone_name}
        super().__init__(coordinator, device)

        self._zone = zone
        self._zone_id = zone.get("station")
        self._attr_unique_id = (
            f"{self._mac_address}:{self._device_id}:{self._zone_id}:history"
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the entity."""
        latest = self._get_latest_irrigation()
        if not latest:
            return None
        start_time = latest.get(ATTR_START_TIME)
        if start_time:
            return orbit_time_to_local_time(start_time)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        latest = self._get_latest_irrigation()
        if not latest:
            return {}

        gallons = latest.get("water_volume_gal")
        litres = round(gallons * 3.785, 2) if gallons else None

        return {
            ATTR_BUDGET: latest.get(ATTR_BUDGET),
            ATTR_PROGRAM: latest.get(ATTR_PROGRAM),
            ATTR_PROGRAM_NAME: latest.get(ATTR_PROGRAM_NAME),
            ATTR_RUN_TIME: latest.get(ATTR_RUN_TIME),
            ATTR_STATUS: latest.get(ATTR_STATUS),
            ATTR_CONSUMPTION_GALLONS: gallons,
            ATTR_CONSUMPTION_LITRES: litres,
            ATTR_START_TIME: latest.get(ATTR_START_TIME),
        }

    def _get_latest_irrigation(self) -> dict | None:
        """
        Return the irrigation entry with the greatest start_time for this zone.

        All statuses are considered — skipped runs can still report flow
        consumption. Ordering is derived from start_time rather than array
        position so we don't depend on how the upstream API sorts entries.
        """
        latest: dict | None = None
        latest_start: str | None = None
        for history_item in self._get_device_history():
            for irrigation in history_item.get(ATTR_IRRIGATION, []):
                if irrigation.get("station") != self._zone_id:
                    continue
                start_time = irrigation.get(ATTR_START_TIME)
                if not start_time:
                    continue
                if latest_start is None or start_time > latest_start:
                    latest_start = start_time
                    latest = irrigation
        return latest

    def _get_device_history(self) -> list:
        """Get device history from coordinator."""
        return (
            self.coordinator.data.get("devices", {})
            .get(self._device_id, {})
            .get("history", [])
        )
