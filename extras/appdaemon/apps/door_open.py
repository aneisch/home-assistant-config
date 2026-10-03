import appdaemon.plugins.hass.hassapi as hass

# Optional args (checked only when turning ON, so off-timers always complete):
#   start_time / end_time - window in which triggers turn lights on (e.g. sunset / sunrise)
#   enable_boolean        - input_boolean(s) that must all be on for triggers to turn lights on
# Don't use constrain_* in apps.yaml for this app: those also block the off-timer.

class DoorLight(hass.Hass):
    def initialize(self):
        self.timer = None
        self.activated = False
        self.device_list = self.split_device_list(self.args["toggle_entity"])

        self.start_time = self.args.get("start_time")
        self.end_time = self.args.get("end_time")
        if self.start_time or self.end_time:
            self.start_time = self.start_time or "00:00:00"
            self.end_time = self.end_time or "23:59:59"

        enable = self.args.get("enable_boolean", [])
        self.enable_booleans = [enable] if isinstance(enable, str) else enable

        # Register listeners for each sensor
        trigger_sensors = self.args.get("trigger_sensor")
        if trigger_sensors:
            for sensor in self.split_device_list(trigger_sensors):
                self.listen_state(self.state_change, sensor)

    def enabled(self):
        if self.start_time and not self.now_is_between(self.start_time, self.end_time):
            return False
        return all(self.get_state(b) == "on" for b in self.enable_booleans)

    def cancel_off_timer(self):
        if self.timer:
            self.cancel_timer(self.timer)
            self.timer = None
            self.log(f"Cancelled scheduled off timer")

    def state_change(self, entity, attribute, old, new, kwargs):
        #self.log(f"{entity} changed from {old} to {new} at {self.time()}")

        # If door opened or sensor triggered
        if old in ["off", "closed"] and new in ["on", "open"]:
            # Keep lights we turned on lit while triggered, even outside the window
            self.cancel_off_timer()

            if not self.enabled():
                return

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
            self.cancel_off_timer()

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
