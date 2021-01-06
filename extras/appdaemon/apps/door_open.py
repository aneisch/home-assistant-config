import appdaemon.plugins.hass.hassapi as hass


class DoorLight(hass.Hass):
    def initialize(self):
        self.timer = None

        if "door_sensor" in self.args:
            for sensor in self.split_device_list(self.args["door_sensor"]):
                self.listen_state(self.state_change, sensor)

    def state_change(self, entity, attribute, old, new, kwargs):
        # Turn on immediately
        if (old in ["off", "closed"]) and (new in ["on", "open"]):

            for device in self.split_device_list(self.args["lights"]):
                if self.get_state(device) == "off":
                    self.log("Turning " + device + " on")
                    self.turn_on(device)

            if self.timer != None:
                self.cancel_timer(self.timer)
                self.log("Cancelled turn_off {}".format(self.timer))

        # Schedule time off for after door/cover closes
        elif (old in ["on", "open"]) and (new in ["off", "closed"]):
            for device in self.split_device_list(self.args["lights"]):
                # Schedule turn_off
                self.timer = self.run_in(self.light_off, self.args["time_on"], device=device)
                self.log("Scheduled turn_off {}".format(self.timer))

    def light_off(self, args):
        self.log("Turning " + args["device"] + " off")
        self.turn_off(args["device"])
        self.timer = None
