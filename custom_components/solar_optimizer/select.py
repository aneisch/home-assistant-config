# pylint: disable=unused-argument

"""A select component for holding the priority"""
import logging

from homeassistant.core import HomeAssistant

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.select import SelectEntity, DOMAIN as SELECT_DOMAIN

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entries of type select for each ManagedDevice"""
    _LOGGER.debug(
        "Calling async_setup_entry entry=%s, data=%s", entry.entry_id, entry.data
    )

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    entities = []
    if entry.data[CONF_DEVICE_TYPE] == CONF_DEVICE_CENTRAL:
        # Central config, create the select entity which holds the priority weight
        entity = SolarOptimizerPriorityWeightSelect(hass, coordinator)
        async_add_entities([entity], False)
        return

    unique_id = name_to_unique_id(entry.data[CONF_NAME])
    device = coordinator.get_device_by_unique_id(unique_id)
    if device is None:
        _LOGGER.error("Calling switch.async_setup_entry in error cause device with unique_id %s not found", unique_id)
        return

    entities = [
        SolarOptimizerPrioritySelect(hass, coordinator, device),
    ]

    async_add_entities(entities)


class SolarOptimizerPriorityWeightSelect(SelectEntity, RestoreEntity):
    """Representation of the central mode choice"""

    def __init__(self, hass: HomeAssistant, coordinator: SolarOptimizerCoordinator):
        """Initialize the PriorityWeightSelect entity."""
        self._hass = hass
        self._coordinator = coordinator
        self._attr_name = "Priority weight"
        self.entity_id = f"{SELECT_DOMAIN}.solar_optimizer_priority_weight"
        self._attr_unique_id = "solar_optimizer_priority_weight"
        self._attr_options = PRIORITY_WEIGHTS
        self._attr_current_option = PRIORITY_WEIGHT_NULL

    @property
    def icon(self) -> str:
        return "mdi:weight"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, CONF_DEVICE_CENTRAL)},
            name="Solar Optimizer",
            manufacturer=DEVICE_MANUFACTURER,
            model=INTEGRATION_MODEL,
        )

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()
        _LOGGER.debug(
            "%s - Calling async_added_to_hass old_state is %s", self, old_state
        )
        if old_state is not None and old_state.state in PRIORITY_WEIGHTS:
            self._attr_current_option = old_state.state

        self._coordinator.set_priority_weight_entity(self)

    @overrides
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        old_option = self._attr_current_option

        if option == old_option:
            return

        if option in PRIORITY_WEIGHTS:
            self._attr_current_option = option
            _LOGGER.info("%s - priority weight has been changed to %s", self, self._attr_current_option)

    @overrides
    def select_option(self, option: str) -> None:
        """Change the selected option"""
        self.hass.create_task(self.async_select_option(option))

    @property
    def current_priority_weight(self) -> int:
        """Return the current weight"""
        # Map the current option string to its corresponding weight value
        return PRIORITY_WEIGHT_MAP.get(self._attr_current_option, 0)  # Default to 0 if not found


class SolarOptimizerPrioritySelect(SelectEntity, RestoreEntity):
    """Representation of the central mode choice"""

    def __init__(self, hass: HomeAssistant, coordinator: SolarOptimizerCoordinator, device: ManagedDevice):
        """Initialize the PriorityWeightSelect entity."""
        self._hass = hass
        idx = name_to_unique_id(device.name)
        self._coordinator = coordinator
        self._device = device
        self._attr_name = "Priority"
        self._attr_has_entity_name = True
        self.entity_id = f"{SELECT_DOMAIN}.solar_optimizer_priority_{idx}"
        self._attr_unique_id = "solar_optimizer_priority_" + idx
        self._attr_options = PRIORITIES
        self._attr_current_option = PRIORITY_MEDIUM
        self._attr_translation_key = "priority"

    @property
    def icon(self) -> str:
        return "mdi:priority-high"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device.name)},
            name="Solar Optimizer-" + self._device.name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @overrides
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()
        _LOGGER.debug("%s - Calling async_added_to_hass old_state is %s", self, old_state)
        if old_state is not None and old_state.state in PRIORITIES:
            self._attr_current_option = old_state.state

        self._device.set_priority_entity(self)

    @overrides
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        old_option = self._attr_current_option

        if option == old_option:
            return

        if option in PRIORITIES:
            self._attr_current_option = option
            _LOGGER.info("%s - priority has been changed to %s", self, self._attr_current_option)

    @overrides
    def select_option(self, option: str) -> None:
        """Change the selected option"""
        self.hass.create_task(self.async_select_option(option))

    @property
    def current_priority(self) -> int:
        """Return the current priority"""
        # Map the current option string to its corresponding priorityvalue
        return PRIORITY_MAP.get(self._attr_current_option, 0)  # Default to 0 if not found
