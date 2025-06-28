import appdaemon.plugins.hass.hassapi as hass
import datetime

class AutoAdjust(hass.Hass):
    def initialize(self):
        # Register proper API endpoint wrappers
        self.register_endpoint(self.api_adjust_morning, "adjust_morning")
        self.register_endpoint(self.api_adjust_night, "adjust_night")
        self.register_endpoint(self.api_adjust_midnight, "adjust_midnight")

        # Parse time strings
        self.morning_adjust_weekday = self.parse_time(self.args["morning_adjust_weekday"])
        self.night_adjust_weekday = self.parse_time(self.args["night_adjust_weekday"])
        self.morning_adjust_weekend = self.parse_time(self.args["morning_adjust_weekend"])
        self.night_adjust_weekend = self.parse_time(self.args["night_adjust_weekend"])
        self.midnight_adjust = self.parse_time(self.args["midnight_adjust"])

        # Schedule adjustments
        self.run_daily(self.adjust_morning, self.morning_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
        self.run_daily(self.adjust_night, self.night_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
        self.run_daily(self.adjust_morning, self.morning_adjust_weekend, constrain_days="sat,sun")
        self.run_daily(self.adjust_night, self.night_adjust_weekend, constrain_days="sat,sun")
        # Only have "midnight" adjustment active when non guest mode
        self.run_daily(self.adjust_midnight, self.midnight_adjust, constrain_input_boolean="input_boolean.guest_mode,off")

        # Debounce window and boost status
        self.boost_active = False
        self.should_boost = None
        self.boost_debounce_handle = None

        # Listen to solar, load, SOC changes
        self.listen_state(self.solar_change_callback, "sensor.solark_sol_ark_solar_power")
        self.listen_state(self.solar_change_callback, "sensor.solark_sol_ark_load_power")
        self.listen_state(self.solar_change_callback, "sensor.solark_sol_ark_battery_soc")


        # Presence detection
        if "device_tracker" in self.args:
            self.listen_state(self.presence_adjust, self.args["device_tracker"])
        if "door_trigger" in self.args:
            for device in self.split_device_list(self.args["door_trigger"]):
                self.listen_state(self.presence_adjust, device)

    def parse_time(self, time_str):
        return datetime.datetime.strptime(time_str, "%H:%M:%S").time()

    def solar_change_callback(self, entity, attribute, old, new, kwargs):
        self.evaluate_boost_conditions()

    def evaluate_boost_conditions(self):
        try:
            solar_power = float(self.get_state("sensor.solark_sol_ark_solar_power") or 0)
            load_power = float(self.get_state("sensor.solark_sol_ark_load_power") or 0)
            battery_soc = float(self.get_state("sensor.solark_sol_ark_battery_soc") or 0)
            self.excess_solar = excess_solar
            self.battery_soc = battery_soc
        
        except (TypeError, ValueError):
            self.log("Skipping boost evaluation due to invalid sensor data", level="WARNING")
            return

        excess_solar = solar_power - load_power
        now = datetime.datetime.now().time()
        start = self.parse_time(self.args["cooldown_window_start"])
        end = self.parse_time(self.args["cooldown_window_end"])

        # Ignore boost if not within boost window
        if not (start <= now <= end):
            self.boost_active = False
            return

        eligible = (
            excess_solar > float(self.args["solar_boost_threshold"])
            and battery_soc > float(self.args["battery_boost_threshold"])
        )

        # If eligibility state changed, debounce the *action*
        if eligible != self.should_boost:
            self.should_boost = eligible
            if self.boost_debounce_handle:
                self.cancel_timer(self.boost_debounce_handle)
            self.boost_debounce_handle = self.run_in(self.commit_boost_change, 600)  # 10 minutes

    def commit_boost_change(self, kwargs):
        if self.should_boost != self.boost_active:
            if self.should_boost:
                self.log(f"Boost Activated: Excess: {self.excess_solar} Battery SOC {self.battery_soc}%")
            else:
                self.log(f"Boost Deactivated: Excess: {self.excess_solar} Battery SOC: {self.battery_soc}%")

            self.boost_active = self.should_boost
            self.adjust_morning()  # apply new temp


    def adjust_temp(self, kwargs):
        for tstat in self.split_device_list(self.args["thermostats"]):
            #self.log(f"Calling Temperature Change: {kwargs['temp']}")
            self.call_service("climate/set_temperature", entity_id=tstat, temperature=kwargs["temp"])

    def presence_adjust(self, entity, attribute, old, new, kwargs):
        if self.get_state("sensor.thermostat_operating_mode").lower() == "off":
            return

        now = datetime.datetime.now().time()

        if (old == "not_home" and new == "home") or (old == "off" and new == "on"):
            self.log(f"Occupied - Presence event triggered by {entity}")
            if self.time_in_range(self.midnight_adjust, self.morning_adjust_weekday, now):
                self.adjust_midnight()
            elif self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, now):
                self.adjust_morning()
            else:
                self.adjust_night()

        elif old == "home" and new == "not_home":
            self.log(f"Unoccupied - Presence event triggered by {entity}")
            mode = self.get_state("sensor.thermostat_operating_mode").lower()
            if mode == "heat":
                self.run_in(self.adjust_temp, 5, temp=self.args["heat_unoccupied"])
            elif mode == "cool":
                self.run_in(self.adjust_temp, 5, temp=self.args["cool_unoccupied"])

    def time_in_range(self, start, end, x):
        if start <= end:
            return start <= x <= end
        else:
            return start <= x or x <= end

    def adjust_morning(self, *args):
        self._adjust_period("morning")

    def adjust_night(self, *args):
        self._adjust_period("night")

    def adjust_midnight(self, *args):
        self._adjust_period("midnight")

    def _adjust_period(self, label):
        #self.log(f"Adjust period '{label}'")

        tracker_state = self.get_state(self.args["device_tracker"])
        mode = self.get_state("sensor.thermostat_operating_mode").lower()

        if mode == "off":
            return

        occupied = tracker_state == "home"
        suffix = "Unoccupied" if not occupied else label.capitalize()

        if mode == "heat":
            temp = self.args[f"heat_{label}"] if occupied else self.args["heat_unoccupied"]

        elif mode == "cool":
            # Boost mode if active and "morning" and someone home
            if self.boost_active and label == "morning" and occupied:
                temp = float(self.args[f"cool_{label}"]) - float(self.args.get("cool_boost_offset", 2))
            else:
                temp = self.args[f"cool_{label}"] if occupied else self.args["cool_unoccupied"]

        self.log(f"Adjust period: '{label}' Mode: '{mode}' Temperature: '{temp}' Boost: '{self.boost_active}'")
        self.run_in(self.adjust_temp, 1, temp=temp)

    # API-compliant wrappers
    def api_adjust_morning(self, *kwargs):
        self.adjust_morning()
        return "OK", 200

    def api_adjust_night(self, *kwargs):
        self.adjust_night()
        return "OK", 200

    def api_adjust_midnight(self, *kwargs):
        self.adjust_midnight()
        return "OK", 200