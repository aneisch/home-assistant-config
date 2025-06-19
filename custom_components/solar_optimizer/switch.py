""" A binary sensor entity that holds the state of each managed_device """

import logging
from datetime import datetime
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_ON
from homeassistant.core import callback, HomeAssistant, State, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.switch import SwitchEntity, DOMAIN as SWITCH_DOMAIN

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)

from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Binary sensor, one for each ManagedDevice"""
    _LOGGER.debug("Calling switch.async_setup_entry")

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    entities = []
    if entry.data[CONF_DEVICE_TYPE] == CONF_DEVICE_CENTRAL:
        return

    unique_id = name_to_unique_id(entry.data[CONF_NAME])
    device = coordinator.get_device_by_unique_id(unique_id)
    if device is None:
        _LOGGER.error("Calling switch.async_setup_entry in error cause device with unique_id %s not found", unique_id)
        return
    # Not needed because the device is created in sensor.py which is the first to be called (see order in const.py)
    #     device = ManagedDevice(hass, entry.data, coordinator)
    #     coordinator.add_device(device)

    entity = ManagedDeviceSwitch(coordinator, hass, device)
    entities.append(entity)
    entity = ManagedDeviceEnable(hass, device)
    entities.append(entity)

    async_add_entities(entities)


class ManagedDeviceSwitch(CoordinatorEntity, SwitchEntity):
    """The entity holding the algorithm calculation"""

    _entity_component_unrecorded_attributes = (
        SwitchEntity._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "is_enabled",
                    "is_active",
                    "is_waiting",
                    "is_usable",
                    "can_change_power",
                    "duration_sec",
                    "duration_power_sec",
                    "power_min",
                    "power_max",
                    "next_date_available",
                    "next_date_available_power",
                    "battery_soc_threshold",
                    "battery_soc",
                }
            )
        )
    )

    def __init__(self, coordinator, hass, device: ManagedDevice):
        _LOGGER.debug("Adding ManagedDeviceSwitch for %s", device.name)
        idx = name_to_unique_id(device.name)
        super().__init__(coordinator, context=idx)
        self._hass: HomeAssistant = hass
        self._device = device
        self.idx = idx
        self._attr_has_entity_name = True
        self.entity_id = f"{SWITCH_DOMAIN}.solar_optimizer_{idx}"
        self._attr_name = "Active"
        self._attr_unique_id = "solar_optimizer_active_" + idx
        self._entity_id = device.entity_id
        self._attr_is_on = device.is_active

        # Try to get the state if it exists
        # device: ManagedDevice = None
        # if (device := coordinator.get_device_by_unique_id(idx)) is not None:
        #    self._device = device
        # else:
        #    self._attr_is_on = None

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

        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(
            self._hass.bus.async_listen(
                event_type=EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
                listener=self._on_enable_state_change,
            )
        )

        self.update_custom_attributes(self._device)

    @callback
    async def _on_enable_state_change(self, event: Event) -> None:
        """Triggered when the ManagedDevice enable state have change"""

        # is it for me ?
        if (
            not event.data
            or (device_id := event.data.get("device_unique_id")) != self.idx
        ):
            return

        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(device_id)
        ):
            return

        _LOGGER.info(
            "Changing enabled state for %s to %s", device_id, device.is_enabled
        )

        self.update_custom_attributes(device)
        self.async_write_ha_state()

    @callback
    async def _on_state_change(self, event: Event) -> None:
        """The entity have change its state"""
        _LOGGER.info(
            "Appel de on_state_change à %s avec l'event %s", datetime.now(), event
        )

        if not event.data:
            return

        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        new_state: State = event.data.get("new_state")
        # old_state: State = event.data.get("old_state")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Pas d'état disponible. Evenement ignoré")
            return

        # On recherche la date de l'event pour la stocker dans notre état
        new_state = self._device.is_active  # new_state.state == STATE_ON
        if new_state == self._attr_is_on:
            return

        self._attr_is_on = new_state
        # On sauvegarde le nouvel état
        self.update_custom_attributes(device)
        self.async_write_ha_state()

    def update_custom_attributes(self, device):
        """Add some custom attributes to the entity"""
        current_tz = get_tz(self._hass)
        self._attr_extra_state_attributes: dict(str, str) = {
            "is_enabled": device.is_enabled,
            "is_active": device.is_active,
            "is_waiting": device.is_waiting,
            "is_usable": device.is_usable,
            "can_change_power": device.can_change_power,
            "current_power": device.current_power,
            "requested_power": device.requested_power,
            "duration_sec": device.duration_sec,
            "duration_power_sec": device.duration_power_sec,
            "power_min": device.power_min,
            "power_max": device.power_max,
            "next_date_available": device.next_date_available.astimezone(
                current_tz
            ).isoformat(),
            "next_date_available_power": device.next_date_available_power.astimezone(
                current_tz
            ).isoformat(),
            "battery_soc_threshold": device.battery_soc_threshold,
            "battery_soc": device.battery_soc,
            "device_name": device.name,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("Calling _handle_coordinator_update for %s", self._attr_name)

        if not self.coordinator or not self.coordinator.data:
            _LOGGER.debug("No coordinator found or no data...")
            return

        device: ManagedDevice = self.coordinator.data.get(self.idx)
        if not device:
            # it is possible to not have device in coordinator update (if device is not enabled)
            _LOGGER.debug("No device %s found ...", self.idx)
            return

        self._attr_is_on = device.is_active
        self.update_custom_attributes(device)
        self.async_write_ha_state()

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.hass.async_create_task(self.async_turn_on(**kwargs))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.info("Turn_on Solar Optimizer switch %s", self._attr_name)
        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        if not self._attr_is_on:
            await device.activate()
            self._attr_is_on = True
            self.update_custom_attributes(device)
            self.async_write_ha_state()
            _LOGGER.debug("Turn_on Solar Optimizer switch %s ok", self._attr_name)

    def turn_off(  # pylint: disable=useless-parent-delegation
        self, **kwargs: Any
    ) -> None:
        """Turn the entity off."""
        # We cannot call async_turn_off from a sync context so we call the async_turn_off in a task
        self.hass.async_create_task(self.async_turn_off(**kwargs))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        _LOGGER.info("Turn_off Solar Optimizer switch %s", self._attr_name)
        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        if self._attr_is_on:
            _LOGGER.debug("Will deactivate %s", self._attr_name)
            await device.deactivate()
            self._attr_is_on = False
            self.update_custom_attributes(device)
            self.async_write_ha_state()
            _LOGGER.debug("Turn_ff Solar Optimizer switch %s ok", self._attr_name)
        else:
            _LOGGER.debug("Not active %s", self._attr_name)

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
    def get_attr_extra_state_attributes(self):
        """Get the extra state attributes for the entity"""
        return self._attr_extra_state_attributes


class ManagedDeviceEnable(SwitchEntity, RestoreEntity):
    """The that enables the ManagedDevice optimisation with"""

    _device: ManagedDevice

    def __init__(self, hass: HomeAssistant, device: ManagedDevice):
        name = name_to_unique_id(device.name)
        self._hass: HomeAssistant = hass
        self._device = device
        self._attr_has_entity_name = True
        self.entity_id = f"{SWITCH_DOMAIN}.enable_solar_optimizer_{name}"
        self._attr_name = "Enable"
        self._attr_unique_id = "solar_optimizer_enable_" + name
        self._attr_is_on = True

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
    def icon(self) -> str | None:
        return "mdi:check"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Récupérer le dernier état sauvegardé de l'entité
        last_state = await self.async_get_last_state()

        # Si l'état précédent existe, vous pouvez l'utiliser
        if last_state is not None:
            self._attr_is_on = last_state.state == STATE_ON
        else:
            # Si l'état précédent n'existe pas, initialisez l'état comme vous le souhaitez
            self._attr_is_on = True

        # this breaks the start of integration
        self.update_device_enabled()

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self.turn_on(**kwargs)

    @callback
    async def async_turn_off(  # pylint: disable=useless-parent-delegation
        self, **kwargs: Any
    ) -> None:
        """Turn the entity off."""
        # We cannot call async_turn_off from a sync context so we call the async_turn_off in a task
        self.turn_off(**kwargs)

    def update_device_enabled(self) -> None:
        """Update the device is enabled flag"""
        if not self._device:
            return

        self._device.set_enable(self._attr_is_on)

    @overrides
    def turn_off(self, **kwargs: Any):
        self._attr_is_on = False
        self.async_write_ha_state()
        self.update_device_enabled()

    @overrides
    def turn_on(self, **kwargs: Any):
        self._attr_is_on = True
        self.async_write_ha_state()
        self.update_device_enabled()
