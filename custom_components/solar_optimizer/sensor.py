""" A sensor entity that holds the result of the recuit simule algorithm """

import logging
from datetime import datetime, timedelta, time
from homeassistant.const import (
    UnitOfPower,
    UnitOfTime,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_ON,
)
from homeassistant.core import callback, HomeAssistant, Event, State
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import entity_platform
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)
from homeassistant.helpers.restore_state import (
    RestoreEntity,
    async_get as restore_async_get,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.device_registry import DeviceInfo


from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Sensor"""

    # check that there is some data to configure
    if (device_type := entry.data.get(CONF_DEVICE_TYPE, None)) is None:
        return

    # Sets the config entries values to SolarOptimizer coordinator
    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    # inititalize the coordinator if entry if the central config
    if device_type == CONF_DEVICE_CENTRAL:
        # This is device entry
        entity1 = SolarOptimizerSensorEntity(coordinator, hass, "best_objective")
        entity2 = SolarOptimizerSensorEntity(coordinator, hass, "total_power")
        entity3 = SolarOptimizerSensorEntity(coordinator, hass, "power_production")
        entity4 = SolarOptimizerSensorEntity(coordinator, hass, "power_production_brut")

        async_add_entities([entity1, entity2, entity3, entity4], False)

        await coordinator.configure(entry)
        return

    entities = []
    device = coordinator.get_device_by_unique_id(
        name_to_unique_id(entry.data[CONF_NAME])
    )
    if device is None:
        device = ManagedDevice(hass, entry.data, coordinator)
        coordinator.add_device(device)

    entity1 = TodayOnTimeSensor(
        hass,
        coordinator,
        device,
    )

    async_add_entities([entity1], False)

    # Add services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESET_ON_TIME,
        {},
        "service_reset_on_time",
    )


class SolarOptimizerSensorEntity(CoordinatorEntity, SensorEntity):
    """The entity holding the algorithm calculation"""

    def __init__(self, coordinator, hass, idx):
        super().__init__(coordinator, context=idx)
        self._hass = hass
        self.idx = idx
        self._attr_name = idx
        self._attr_unique_id = "solar_optimizer_" + idx

        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (
            not self.coordinator
            or not self.coordinator.data
            or (value := self.coordinator.data.get(self.idx)) is None
        ):
            _LOGGER.debug("No coordinator found or no data...")
            return

        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        # Retournez des informations sur le périphérique associé à votre entité
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, CONF_DEVICE_CENTRAL)},
            name="Solar Optimizer",
            manufacturer=DEVICE_MANUFACTURER,
            model=INTEGRATION_MODEL,
        )

    @property
    def icon(self) -> str | None:
        if self.idx == "best_objective":
            return "mdi:bullseye-arrow"
        elif self.idx == "total_power":
            return "mdi:flash"
        elif self.idx == "battery_soc":
            return "mdi:battery"
        else:
            return "mdi:solar-power-variant"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if self.idx == "best_objective":
            return SensorDeviceClass.MONETARY
        elif self.idx == "battery_soc":
            return SensorDeviceClass.BATTERY
        else:
            return SensorDeviceClass.POWER

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.device_class == SensorDeviceClass.POWER:
            return SensorStateClass.MEASUREMENT
        else:
            return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.idx == "best_objective":
            return "€"
        elif self.idx == "battery_soc":
            return "%"
        else:
            return UnitOfPower.WATT


class TodayOnTimeSensor(SensorEntity, RestoreEntity):
    """Gives the time in minute in which the device was on for a day"""

    _entity_component_unrecorded_attributes = (
        SensorEntity._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "max_on_time_per_day_sec",
                    "max_on_time_per_day_min",
                    "max_on_time_hms",
                    "on_time_hms",
                    "raz_time",
                    "should_be_forced_offpeak",
                }
            )
        )
    )

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: SolarOptimizerCoordinator,
        device: ManagedDevice,
    ) -> None:
        """Initialize the sensor"""
        self.hass = hass
        idx = name_to_unique_id(device.name)
        self._attr_name = "On time today"
        self._attr_has_entity_name = True
        self.entity_id = f"{SENSOR_DOMAIN}.on_time_today_solar_optimizer_{idx}"
        self._attr_unique_id = "solar_optimizer_on_time_today_" + idx
        self._attr_native_value = None
        self._entity_id = device.entity_id
        self._device = device
        self._coordinator = coordinator
        self._last_datetime_on = None
        self._old_state = None

    async def async_added_to_hass(self) -> None:
        """The entity have been added to hass, listen to state change of the underlying entity"""
        await super().async_added_to_hass()

        # Arme l'écoute de la première entité
        listener_cancel = async_track_state_change_event(
            self.hass,
            [self._entity_id],
            self._on_state_change,
        )
        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(listener_cancel)

        # Add listener to midnight to reset the counter
        raz_time: time = self._coordinator.raz_time
        self.async_on_remove(
            async_track_time_change(
                hass=self.hass,
                action=self._on_midnight,
                hour=raz_time.hour,
                minute=raz_time.minute,
                second=0,
            )
        )

        # Add a listener to calculate OnTine at each minute
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._on_update_on_time,
                interval=timedelta(minutes=1),
            )
        )

        # restore the last value or set to 0
        self._attr_native_value = 0
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.state is not None and old_state.state != "unknown":
                self._attr_native_value = round(float(old_state.state))
                _LOGGER.info(
                    "%s - read on_time from storage is %s",
                    self,
                    self._attr_native_value,
                )

            old_value = old_state.attributes.get("last_datetime_on")
            if old_value is not None:
                self._last_datetime_on = datetime.fromisoformat(old_value)

        self.update_custom_attributes()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Try to force backup of entity"""
        _LOGGER.info(
            "%s - force write before remove. on_time is %s",
            self,
            self._attr_native_value,
        )
        # Force dump in background
        await restore_async_get(self.hass).async_dump_states()

    @callback
    async def _on_state_change(self, event: Event) -> None:
        """The entity have change its state"""
        now = self._device.now
        _LOGGER.info("Call of on_state_change at %s with event %s", now, event)

        if not event.data:
            return

        new_state: State = event.data.get("new_state")
        # old_state: State = event.data.get("old_state")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("No available state. Event is ignored")
            return

        need_save = False
        # We search for the date of the event
        new_state = self._device.is_active  # new_state.state == STATE_ON
        # old_state = old_state is not None and old_state.state == STATE_ON
        if new_state and not self._old_state:
            _LOGGER.debug("The managed device becomes on - store the last_datetime_on")
            self._last_datetime_on = now
            need_save = True

        if not new_state:
            if self._old_state and self._last_datetime_on is not None:
                _LOGGER.debug("The managed device becomes off - increment the delta time")
                self._attr_native_value += round((now - self._last_datetime_on).total_seconds())
            self._last_datetime_on = None
            need_save = True

        # On sauvegarde le nouvel état
        if need_save:
            self._old_state = new_state
            self.update_custom_attributes()
            self.async_write_ha_state()
            self._device.set_on_time(self._attr_native_value)

    @callback
    async def _on_midnight(self, _=None) -> None:
        """Called each day at midnight to reset the counter"""
        self._attr_native_value = 0

        _LOGGER.info("Call of _on_midnight to reset onTime")

        # reset _last_datetime_on to now if it was active. Here we lose the time on of yesterday but it is too late I can't do better.
        # Else you will have two point with the same date and not the same value (one with value + duration and one with 0)
        if self._last_datetime_on is not None:
            self._last_datetime_on = self._device.now

        self.update_custom_attributes()
        self.async_write_ha_state()
        self._device.set_on_time(self._attr_native_value)

    @callback
    async def _on_update_on_time(self, _=None) -> None:
        """Called priodically to update the on_time sensor"""
        now = self._device.now
        _LOGGER.debug("Call of _on_update_on_time at %s", now)

        if self._last_datetime_on is not None and self._device.is_active:
            self._attr_native_value += round(
                (now - self._last_datetime_on).total_seconds()
            )
            self._last_datetime_on = now
            self.update_custom_attributes()
            self.async_write_ha_state()

            self._device.set_on_time(self._attr_native_value)

    def update_custom_attributes(self):
        """Add some custom attributes to the entity"""
        self._attr_extra_state_attributes: dict(str, str) = {
            "last_datetime_on": self._last_datetime_on,
            "max_on_time_per_day_min": round(self._device.max_on_time_per_day_sec / 60),
            "max_on_time_per_day_sec": self._device.max_on_time_per_day_sec,
            "on_time_hms": seconds_to_hms(self._attr_native_value),
            "max_on_time_hms": seconds_to_hms(self._device.max_on_time_per_day_sec),
            "raz_time": self._coordinator.raz_time,
            "should_be_forced_offpeak": self._device.should_be_forced_offpeak,
            "offpeak_time": self._device.offpeak_time,
        }

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_info(self) -> DeviceInfo | None:
        # Retournez des informations sur le périphérique associé à votre entité
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device.name)},
            name="Solar Optimizer-" + self._device.name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfTime.SECONDS

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 0

    @property
    def last_datetime_on(self) -> datetime | None:
        """Returns the last_datetime_on"""
        return self._last_datetime_on

    @property
    def get_attr_extra_state_attributes(self):
        """Get the extra state attributes for the entity"""
        return self._attr_extra_state_attributes

    async def service_reset_on_time(self):
        """Called by a service call:
        service: sensor.reset_on_time
        data:
        target:
            entity_id: solar_optimizer.on_time_today_solar_optimizer_<device name>
        """
        _LOGGER.info("%s - Calling service_reset_on_time", self)
        await self._on_midnight()
