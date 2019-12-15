import appdaemon.plugins.hass.hassapi as hass

# Simple app to have entities follow the state of another

class Follow(hass.Hass):
    def initialize(self):
        for entity in self.split_device_list(self.args["leader"]):
            self.listen_state(self.state_change, entity)

    def state_change(self, entity, attribute, old, new, kwargs):
        if new == "on" and old != "unavailable" and old != "Unavailable":
            for device in self.split_device_list(self.args["follower"]):
                if "invert" in self.args:
                    self.log("Turning off " + device)
                    self.turn_off(device)
                else:
                    self.log("Turning on " + device)
                    self.turn_on(device)

        elif new == "off" and old != "unavailable" and old != "Unavailable":
            for device in self.split_device_list(self.args["follower"]):
                if "invert" in self.args:
                    self.log("Turning on " + device)
                    self.turn_on(device)
                else:
                    self.log("Turning off " + device)
                    self.turn_off(device)
