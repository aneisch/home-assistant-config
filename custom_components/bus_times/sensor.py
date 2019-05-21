"""
This custom component provides HA sensor for bus times
"""

import datetime
from datetime import timedelta
import logging
from bs4 import BeautifulSoup
from urllib.request import urlopen
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Bus Time'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([Reminder("next_bus_home","home")])
    add_devices([Reminder("next_bus_work","work")])


class Reminder(Entity):
    """Implementation of the date reminder sensor."""

    def __init__(self, sensor_name, route):
        """Initialize the sensor."""
        self._route = route
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

    #@property
    #def device_state_attributes(self):
    #    return {
    #        ATTR_TIME: self._data.get("next_time")
    #    }

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return 'mdi:bus-clock'

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):

        times = []

        #Put the url of your route here
        html = urlopen('BUS_URL').read()
        soup = BeautifulSoup(html,features="html.parser")
        initial = str(soup.findAll('table', attrs={'class':'timetable'}))
        processed = initial.split("\n")

        for line in processed:
            time_list = []
            if "datetime" in line:
                soup = BeautifulSoup(line,features="html.parser")
                time = soup.find_all("time")
                if time != []:
                    times.append(time)

        for roundtrip in times:
            if len(roundtrip) == 3:
                home = roundtrip[0]['datetime']
                work = roundtrip[2]['datetime']
            elif len(roundtrip) == 4:
                home = roundtrip[1]['datetime']
                work = roundtrip[3]['datetime']

            home = datetime.datetime.strptime(home, '%m/%d/%Y %I:%M:00 %p')
            work = datetime.datetime.strptime(work, '%m/%d/%Y %I:%M:00 %p')

            if self._route == "home":
                route = home
            elif self._route == "work":
                route = work

            if route < datetime.datetime.now():
                expired = True
            else:
                expired = False

            if expired == True:
                continue
            else:
                break

        try:
            if route < datetime.datetime.now():
                route = "Check back tomorrow"
        except:
                route = "Error"

        self._state = route
