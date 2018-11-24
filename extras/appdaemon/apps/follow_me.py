import appdaemon.plugins.hass.hassapi as hass

# Simple app to have entities follow the state of another

class Follow(hass.Hass):
    def initialize(self):
        for entity in self.split_device_list(self.args["leader"]):
            self.listen_state(self.state_change, entity)

    def state_change(self, entity, attribute, old, new, kwargs):
        if new == "on":
            for device in self.split_device_list(self.args["follower"]):
                self.log("Turning on " + device)
                self.turn_on(device)
        elif new == "off":
            for device in self.split_device_list(self.args["follower"]):
                self.log("Turning on " + device)
                self.turn_off(device)
