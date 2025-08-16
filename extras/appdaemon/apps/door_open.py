import appdaemon.plugins.hass.hassapi as hass

class DoorLight(hass.Hass):
    def initialize(self):
        self.timer = None
        self.activated = False
        self.device_list = self.split_device_list(self.args["toggle_entity"])

        # Register listeners for each sensor
        trigger_sensors = self.args.get("trigger_sensor")
        if trigger_sensors:
            for sensor in self.split_device_list(trigger_sensors):
                self.listen_state(self.state_change, sensor)

    def state_change(self, entity, attribute, old, new, kwargs):
        #self.log(f"{entity} changed from {old} to {new} at {self.time()}")

        # If door opened or sensor triggered
        if old in ["off", "closed"] and new in ["on", "open"]:
            if self.timer:
                self.cancel_timer(self.timer)
                self.log(f"Cancelled scheduled off timer")

            for device in self.device_list:
                if self.get_state(device) == "off":
                    self.log(f"Turning on {device}")
                    if "brightness" in self.args:
                        self.turn_on(device, brightness=self.args["brightness"])
                    else:
                        self.turn_on(device)
                    self.activated = True

        # If door closed and light was turned on by us
        elif (
            old in ["on", "open"] and new in ["off", "closed"]
            and self.activated
            and "time_on" in self.args
        ):
            if self.timer:
                self.cancel_timer(self.timer)
                self.log(f"Cancelled previous off timer")

            delay = int(self.args["time_on"])
            self.timer = self.run_in(self.light_off, delay)
            self.log(f"Scheduled light off in {delay} seconds")

    def light_off(self, kwargs):
        self.log("Executing light off")
        for device in self.device_list:
            self.turn_off(device)
            self.log(f"Turned off {device}")

        self.activated = False
        self.timer = None
