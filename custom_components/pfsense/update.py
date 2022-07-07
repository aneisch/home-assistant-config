"""pfSense integration."""
import logging
import time
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.components.update.const import UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from . import CoordinatorEntityManager, PfSenseEntity, dict_get
from .const import COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
):
    """Set up the pfSense update entities."""

    @callback
    def process_entities_callback(hass, config_entry):
        data = hass.data[DOMAIN][config_entry.entry_id]
        coordinator = data[COORDINATOR]
        entities = []
        entity = PfSenseFirmwareUpdatesAvailableUpdate(
            config_entry,
            coordinator,
            UpdateEntityDescription(
                key=f"firmware.update_available",
                name="Firmware Updates Available",
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            True,
        )
        entities.append(entity)

        return entities

    cem = CoordinatorEntityManager(
        hass,
        hass.data[DOMAIN][config_entry.entry_id][COORDINATOR],
        config_entry,
        process_entities_callback,
        async_add_entities,
    )
    cem.process_entities()


class PfSenseUpdate(PfSenseEntity, UpdateEntity):
    def __init__(
        self,
        config_entry,
        coordinator: DataUpdateCoordinator,
        entity_description: UpdateEntityDescription,
        enabled_default: bool,
    ) -> None:
        """Initialize the sensor."""
        self.config_entry = config_entry
        self.entity_description = entity_description
        self.coordinator = coordinator
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_name = f"{self.pfsense_device_name} {entity_description.name}"
        self._attr_unique_id = slugify(
            f"{self.pfsense_device_unique_id}_{entity_description.key}"
        )

        self._attr_supported_features |= (
            UpdateEntityFeature.INSTALL
            # | UpdateEntityFeature.BACKUP
            # | UpdateEntityFeature.PROGRESS
            # | UpdateEntityFeature.RELEASE_NOTES
            # | UpdateEntityFeature.SPECIFIC_VERSION
        )

    @property
    def device_class(self):
        return UpdateDeviceClass.FIRMWARE


class PfSenseFirmwareUpdatesAvailableUpdate(PfSenseUpdate):
    @property
    def available(self):
        state = self.coordinator.data
        if state["firmware_update_info"] is None:
            return False

        return super().available

    @property
    def title(self):
        return "pfSense"

    @property
    def installed_version(self):
        """Version installed and in use."""
        state = self.coordinator.data

        try:
            return dict_get(state, "firmware_update_info.base.installed_version")
        except KeyError:
            return None

    @property
    def latest_version(self):
        """Latest version available for install."""
        state = self.coordinator.data

        try:
            # fake a new update
            # return "foobar"
            return dict_get(state, "firmware_update_info.base.version")
        except KeyError:
            return None

    @property
    def in_progress(self):
        """Update installation in progress."""
        return False

    @property
    def extra_state_attributes(self):
        state = self.coordinator.data
        attrs = {}

        for key in dict_get(state, "firmware_update_info.base", {}).keys():
            attrs[f"pfsense_base_{key}"] = dict_get(
                state, f"firmware_update_info.base.{key}"
            )

        return attrs

    @property
    def release_url(self):
        return "https://docs.netgate.com/pfsense/en/latest/releases/index.html"

    def install(self, version=None, backup=False):
        """Install an update."""
        client = self._get_pfsense_client()
        pid = client.upgrade_firmware()

        sleep_time = 10
        running = True
        while running:
            time.sleep(sleep_time)
            running = client.pid_is_running(pid)
