import appdaemon.plugins.hass.hassapi as hass
import datetime

class AutoAdjust(hass.Hass):
    def initialize(self):
        # Register API endpoints
        self.register_endpoint(self.adjust_night, "adjust_night")
        self.register_endpoint(self.adjust_morning, "adjust_morning")
        self.register_endpoint(self.adjust_midnight, "adjust_midnight")

        # Parse time strings into time objects
        # Weekday
        self.morning_adjust_weekday = datetime.datetime.strptime(self.args["morning_adjust_weekday"], '%H:%M:%S').time()
        self.night_adjust_weekday = datetime.datetime.strptime(self.args["night_adjust_weekday"], '%H:%M:%S').time()
        # Weekend
        self.morning_adjust_weekend = datetime.datetime.strptime(self.args["morning_adjust_weekend"], '%H:%M:%S').time()
        self.night_adjust_weekend = datetime.datetime.strptime(self.args["night_adjust_weekend"], '%H:%M:%S').time()
        # Always
        self.midnight_adjust = datetime.datetime.strptime(self.args["midnight_adjust"], '%H:%M:%S').time()

        # Time-based scheduling
        # Weekday
        self.run_daily(self.adjust_morning, self.morning_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
        self.run_daily(self.adjust_night, self.night_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
        # Weekend
        self.run_daily(self.adjust_morning, self.morning_adjust_weekend, constrain_days="sat,sun")
        self.run_daily(self.adjust_night, self.night_adjust_weekend, constrain_days="sat,sun")
        # Always
        self.run_daily(self.adjust_midnight, self.midnight_adjust, constrain_days="mon,tue,wed,thu,fri,sat,sun")

        # Presence detection
        if "device_tracker" in self.args:
            for device in self.split_device_list(self.args["device_tracker"]):
                self.listen_state(self.presence_adjust, device)

        if "door_trigger" in self.args:
            for device in self.split_device_list(self.args["door_trigger"]):
                self.listen_state(self.presence_adjust, device)

    def time_in_range(self, start, end, x):
        if start <= end:
            return start <= x <= end
        else:
            return start <= x or x <= end

    def adjust_temp(self, kwargs):
        for tstat in self.split_device_list(self.args["thermostats"]):
            self.call_service("climate/set_temperature", entity_id=tstat, temperature=kwargs["temp"])

    def presence_adjust(self, entity, attribute, old, new, kwargs):
        if self.get_state("sensor.thermostat_operating_mode").lower() == "off":
            return

        now = datetime.datetime.now().time()

        if (old == "not_home" and new == "home") or (old == "off" and new == "on" and self.get_state(self.args["device_tracker"]) == "not_home"):
            self.log(f"Presence event triggered by {entity}")

            if self.time_in_range(self.midnight_adjust, self.morning_adjust_weekday, now):
                self.log("Presence: Midnight period")
                self.adjust_midnight(kwargs)
            elif self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, now):
                self.log("Presence: Day period")
                self.adjust_morning(kwargs)
            else:
                self.log("Presence: Night period")
                self.adjust_night(kwargs)

        elif old == "home" and new == "not_home":
            mode = self.get_state("sensor.thermostat_operating_mode").lower()
            if mode == "heat":
                self.log("Mode: Heat Unoccupied -- %s" % self.args["heat_unoccupied"])
                self.run_in(self.adjust_temp, 5, temp=self.args["heat_unoccupied"])
            elif mode == "cool":
                self.log("Mode: Cool Unoccupied -- %s" % self.args["cool_unoccupied"])
                self.run_in(self.adjust_temp, 5, temp=self.args["cool_unoccupied"])

    def adjust_morning(self, *kwargs):
        return self._adjust_period("morning", kwargs)

    def adjust_night(self, *kwargs):
        return self._adjust_period("night", kwargs)

    def adjust_midnight(self, *kwargs):
        return self._adjust_period("midnight", kwargs)

    def _adjust_period(self, label, kwargs):
        tracker_state = self.get_state(self.args["device_tracker"])
        mode = self.get_state("sensor.thermostat_operating_mode").lower()

        if mode == "off":
            return "", 200

        occupied = tracker_state == "home"
        suffix = "Unoccupied" if not occupied else label.capitalize()

        if mode == "heat":
            temp = self.args[f"heat_{label}"] if occupied else self.args["heat_unoccupied"]
            self.log(f"Mode: Heat {suffix} -- {temp}")
            self.run_in(self.adjust_temp, 1, temp=temp)

        elif mode == "cool":
            temp = self.args[f"cool_{label}"] if occupied else self.args["cool_unoccupied"]
            self.log(f"Mode: Cool {suffix} -- {temp}")
            self.run_in(self.adjust_temp, 1, temp=temp)

        return "", 200