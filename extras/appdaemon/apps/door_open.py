import appdaemon.plugins.hass.hassapi as hass


class DoorLight(hass.Hass):
    def initialize(self):
        if "door_sensor" in self.args:
            for sensor in self.split_device_list(self.args["door_sensor"]):
                self.listen_state(self.state_change, sensor)

    def state_change(self, entity, attribute, old, new, kwargs):
        for device in self.split_device_list(self.args["lights"]):
            if new == "on" and self.get_state(device) == "off":
                self.log("Turning " + device + " On")
                self.turn_on(device)
                # Schedule the turn off
                self.run_in(self.light_off, self.args["time_on"], device=device)

    def light_off(self, args):
        self.log("Turning " + args["device"] + " Off")
        self.turn_off(args["device"])


class DoorNotify(hass.Hass):
    def initialize(self):
        if "door_sensor" in self.args:
            for sensor in self.split_device_list(self.args["door_sensor"]):
                self.listen_state(self.state_change, sensor)

    def state_change(self, entity, attribute, old, new, kwargs):
        if entity == "binary_sensor.front_door" and new == "on":
            self.log(entity + "changed to opened, notifying")
            self.call_service("notify/" + self.args["notify"], title = "Home Assistant", message = "Front Door Opened")

        elif entity == "binary_sensor.back_door" and new == "on":
            self.log(entity + "changed to opened, notifying")
            self.call_service("notify/" + self.args["notify"], title = "Home Assistant", message = "Back Door Opened")
