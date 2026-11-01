# pylint: disable=line-too-long
"""Provides mixin to be used in all entities to drive availability from cloud status or connection status."""

import logging

from lennoxs30api import lennox_system

from . import Manager

_LOGGER = logging.getLogger(__name__)


class S30BaseEntityMixin:
    """Base Class."""

    def __init__(self, manager: Manager, system: lennox_system) -> None:
        """Initialize base mixin."""
        self._manager: Manager = manager
        self._system: lennox_system = system

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._manager.registerConnectionStateCallback(self.connection_state_callback)
        if self.base_ignore_cloud_status is False:
            self._system.registerOnUpdateCallback(
                self.cloud_status_update_callback,
                [
                    "cloud_status",
                ],
            )
        await super().async_added_to_hass()

    @property
    def base_ignore_cloud_status(self) -> bool:
        """Override to ignore cloud status in the entity."""
        return False

    def cloud_status_update_callback(self) -> None:
        """Process cloud statuts updates."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("cloud_status_update_callback cloud_status [%s]", self._system.cloud_status)
        self.schedule_update_ha_state()

    def connection_state_callback(self, connected: bool) -> None:
        """Process connection state updates."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("connection_state_callback connected [%s]", connected)
        self.schedule_update_ha_state()

    @property
    def available(self) -> bool:
        """Determines if entity is available."""
        if self._manager.connected is False:
            return False
        if self.base_ignore_cloud_status is False and self._system.cloud_status == "offline":
            return False
        return super().available

    def update(self) -> bool:
        """Update data from the thermostat API."""
        return True

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False
