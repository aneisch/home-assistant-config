import appdaemon.plugins.hass.hassapi as hass


class DoorLight(hass.Hass):
    def initialize(self):
        if "door_sensor" in self.args:
            for sensor in self.split_device_list(self.args["door_sensor"]):
                self.listen_state(self.state_change, sensor)

    def state_change(self, entity, attribute, old, new, kwargs):
        # Only respond when closed -- > open
        if (old == "on" or old == "closed") and (new == "on" or new == "open"):
            for device in self.split_device_list(self.args["lights"]):
                if self.get_state(device) == "off":
                    self.log("Turning " + device + " On")
                    self.turn_on(device)
                    # Schedule the turn off
                    self.run_in(self.light_off, self.args["time_on"], device=device)

    def light_off(self, args):
        self.log("Turning " + args["device"] + " Off")
        self.turn_off(args["device"])
