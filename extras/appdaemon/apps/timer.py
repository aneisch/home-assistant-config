import appdaemon.plugins.hass.hassapi as hass
import datetime
from datetime import timedelta
import time

# Simple app to get a precise countdown from Alexa timer

class Timer(hass.Hass):
    def initialize(self):
        self.listen_state(self.state_change, self.args["timer_entity"])

    def state_change(self, entity, attribute, old, new, kwargs):
        countdown_destination_entity = self.args["countdown_destination_entity"]
        if new == "unknown" or new == "unavailable":
            state = "No Timers Set"
            self.set_state(countdown_destination_entity, state=state)
            if self.args["mqtt"]:
                self.call_service("mqtt/publish", topic="appdaemon/" + countdown_destination_entity, payload=state)
        else:
            new_stripped = new[:-6]
            datetime_object = datetime.datetime.strptime(new_stripped, '%Y-%m-%dT%H:%M:%S')
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
                    state = "Expired"
                    self.set_state(countdown_destination_entity, state=state)
                    if self.args["mqtt"]:
                        self.call_service("mqtt/publish", topic="appdaemon/" + countdown_destination_entity, payload=state)
                    self.log("Timer Expired")
                    break
                state = str(remaining)[:-7]
                self.set_state(countdown_destination_entity, state=state)
                if self.args["mqtt"]:
                    self.call_service("mqtt/publish", topic="appdaemon/" + countdown_destination_entity, payload=state)
                time.sleep(1)
