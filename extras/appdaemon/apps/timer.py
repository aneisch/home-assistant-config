import appdaemon.plugins.hass.hassapi as hass
import datetime
from datetime import timedelta
import time

# Simple app to get a precise countdown from Alexa timer

class Timer(hass.Hass):
    def initialize(self):
        self.listen_state(self.state_change, self.args["timer_entity"])

    def state_change(self, entity, attribute, old, new, kwargs):
        if new == "unknown":
            self.set_state(self.args["countdown_destination_entity"], state = "No Timers Set")
        else:
            new_stripped = new[:-6]
            datetime_object = datetime.datetime.strptime(new_stripped, '%Y-%m-%d %H:%M:%S.%f')
            remaining = datetime_object - datetime.datetime.now()
            self.log("New timer set: {} from now, ending at {}".format(remaining,new))
            while True:
                state = self.get_state(self.args["timer_entity"])
                remaining = datetime_object - datetime.datetime.now()
                seconds = remaining.total_seconds()
                if state != new:
                    self.log("Timer Changed, Stopping Loop")
                    break
                elif seconds <= 0:
                    self.set_state(self.args["countdown_destination_entity"], state = "Expired")
                    self.log("Timer Expired")
                    break
                self.set_state(self.args["countdown_destination_entity"], state = str(remaining)[:-7])
                time.sleep(1)
