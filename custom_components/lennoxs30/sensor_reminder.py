"""Support for Lennoxs30 maintenance reminder sensors"""

# pylint: disable=line-too-long
# pylint: disable=invalid-name
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util
from lennoxs30api import lennox_system
from lennoxs30api.lennox_reminder import LennoxReminder

from . import Manager
from .base_entity import S30BaseEntityMixin
from .const import LENNOX_DOMAIN, UNIQUE_ID_SUFFIX_REMINDER

_LOGGER = logging.getLogger(__name__)

EXPIRY_TYPE_CALENDAR = "systemCalendarTime"
EXPIRY_TYPE_RUNTIME = "systemRunTime"


class S30ReminderSensor(S30BaseEntityMixin, SensorEntity):
    """Maintenance reminder (filter, UV bulb, humidifier pad, etc.), state is the percent remaining."""

    # Only enabled and expired change in a way worth keeping in history
    _unrecorded_attributes = frozenset(
        {"kind", "expiry_type", "reminder_time", "remaining_runtime", "set_time", "expiry_time", "expired_time", "viewed"}
    )

    def __init__(self, hass: HomeAssistant, manager: Manager, system: lennox_system, reminder: LennoxReminder) -> None:
        super().__init__(manager, system)
        self._hass = hass
        self._reminder: LennoxReminder = reminder
        self._myname = f"{self._system.name}_reminder_{reminder.kind}"
        # Only reminders configured on the thermostat are enabled by default
        self._attr_entity_registry_enabled_default = reminder.enabled is True

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.debug("async_added_to_hass S30ReminderSensor myname [%s]", self._myname)
        self._reminder.register_on_update_callback(self.update_callback)
        await super().async_added_to_hass()

    def update_callback(self) -> None:
        """Callback to execute on data change"""
        _LOGGER.debug("update_callback S30ReminderSensor myname [%s]", self._myname)
        self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        return (self._system.unique_id + UNIQUE_ID_SUFFIX_REMINDER + str(self._reminder.reminder_id)).replace("-", "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs: dict[str, Any] = {}
        attrs["kind"] = self._reminder.kind
        attrs["enabled"] = self._reminder.enabled
        attrs["expired"] = self._reminder.expired
        attrs["expiry_type"] = self._reminder.expiry_type
        attrs["reminder_time"] = self._reminder.reminder_time
        attrs["remaining_runtime"] = self._remaining_runtime_hours()
        attrs["set_time"] = self._reminder_timestamp(self._reminder.set_time)
        attrs["expiry_time"] = self._reminder_timestamp(self._reminder.expiry_time)
        attrs["expired_time"] = self._reminder_timestamp(self._reminder.expired_time)
        attrs["viewed"] = self._reminder.viewed
        return attrs

    def _reminder_timestamp(self, value: int | None) -> datetime | None:
        """Calendar reminders report epoch seconds, converted to a UTC timestamp (0 means not set).

        Run time reminders report positions on the system run time counter, which are not times.
        """
        if self._reminder.expiry_type != EXPIRY_TYPE_CALENDAR or not value:
            return None
        return dt_util.utc_from_timestamp(value)

    def _remaining_runtime_hours(self) -> int | None:
        """Run time left on a run time reminder, estimated from the percent remaining and the interval.

        The thermostat reports whole percents, so this moves in steps of 1% of the interval.
        """
        if self._reminder.expiry_type != EXPIRY_TYPE_RUNTIME or self._reminder.remaining_pct is None or not self._reminder.reminder_time:
            return None
        return round(self._reminder.remaining_pct / 100 * self._reminder.reminder_time / 3600)

    @property
    def name(self) -> str:
        return self._myname

    @property
    def native_value(self) -> int | None:
        if self._reminder.enabled is not True or self._reminder.is_valid is not True:
            return None
        return self._reminder.remaining_pct

    @property
    def native_unit_of_measurement(self) -> str:
        return PERCENTAGE

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(LENNOX_DOMAIN, self._system.unique_id)},
        }
