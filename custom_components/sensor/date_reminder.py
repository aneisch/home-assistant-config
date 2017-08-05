"""
Date Reminder
"""

import datetime
from datetime import timedelta
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ATTR_DAYS = 'days_since'
ATTR_REMAINING = 'days_remaining'

DEFAULT_NAME = "Countdown"
CONF_DATE = 'date'
CONF_REMINDER = 'day_reminder'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DATE): cv.string,
    vol.Required(CONF_REMINDER): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up date countdown sensor."""
    start_date = config.get(CONF_DATE)
    day_reminder = config.get(CONF_REMINDER)
    sensor_name = config.get(CONF_NAME)

    add_devices([Reminder(sensor_name, start_date, day_reminder)])


class Reminder(Entity):
    """Implementation of the date countdown sensor."""

    def __init__(self, sensor_name, start_date, day_reminder):
        """Initialize the sensor."""
        self.start_date = start_date
        self.day_reminder = day_reminder
        self._name = sensor_name
        self._state = None
        self._data = {}
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        return {
            ATTR_DAYS: self._data.get("days_since"),
            ATTR_REMAINING: self._data.get("days_remaining"),
        }

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:calendar'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Calculate time since start"""
        start_date = datetime.datetime.strptime(self.start_date, '%d-%m-%Y %H:%M')
        days = (datetime.datetime.now() - start_date)

        days = days.days

        self._data["days_since"] = days
        self._data["days_remaining"] = int(self.day_reminder) - days

        if days >= int(self.day_reminder):
          self._state = True
        else:
          self._state = False
