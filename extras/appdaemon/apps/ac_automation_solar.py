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
            self.listen_state(self.occupancy_changed, self.args["device_tracker"])
        # if "door_trigger" in self.args:
        #     for device in self.split_device_list(self.args["door_trigger"]):
        #         self.listen_state(self.presence_adjust, device)

    def parse_time(self, time_str):
        return datetime.datetime.strptime(time_str, "%H:%M:%S").time()

    def solar_change_callback(self, entity, attribute, old, new, kwargs):
        self.evaluate_boost_conditions()

    def grid_online(self):
        state = self.get_state(self.args["grid_state_sensor"])
        return state == "on" or state == "true"

    def evaluate_boost_conditions(self):
        # Not within window
        now = datetime.datetime.now().time()
        start = self.parse_time(self.args["cooldown_window_start"])
        end = self.parse_time(self.args["cooldown_window_end"])

        if not (start <= now <= end):
            self.boost_active = False
            return

        # Boost eval disabled
        if self.get_state("input_boolean.ac_boost_feature_evaluation") == "off":
            self.log("Boost Evaluation Disabled by Boolean")
            return

        try:
            solar_power = float(self.get_state("sensor.solark_sol_ark_solar_power") or 0)
            load_power = float(self.get_state("sensor.solark_sol_ark_load_power") or 0)
            # This basically equates to the power going to the battery
            # in the future maybe best to just use grid export power instad of arithmetic 
            excess_solar = solar_power - load_power
            battery_soc = float(self.get_state("sensor.solark_sol_ark_battery_soc") or 0)
            self.excess_solar = excess_solar
            self.battery_soc = battery_soc

        except (TypeError, ValueError):
            self.log("Invalid sensor data", level="WARNING")
            return

        # Prevent boost if grid outage
        if not self.grid_online():
            self.should_boost = False
            if self.boost_active:
                self.log("Boost deactivated because grid went offline", level="INFO")
                self.commit_boost_change({})
            return

        eligible = (
            excess_solar > float(self.args["solar_boost_threshold"])
            and battery_soc >= float(self.args["battery_boost_threshold"])  # allow equality
        )

        #self.log(f"Boost Evaluation Result: {eligible} - Excess: {excess_solar}W Battery SOC {battery_soc}%", level="INFO")

        if eligible != self.should_boost:
            self.log(f"Eligibility changed --> {eligible} (was {self.should_boost})", level="INFO")
            self.should_boost = eligible

            # Cancel any pending debounce
            if self.boost_debounce_handle:
                self.cancel_timer(self.boost_debounce_handle)
                self.boost_debounce_handle = None
                self.log(f"Boost Deactivation Cancelled")

            if eligible:
                # Immediate ON
                self.commit_boost_change({})
            else:
                # Delay OFF
                self.log(f"Boost Deactivation Scheduled")
                self.boost_debounce_handle = self.run_in(self.commit_boost_change, 300)  # 5 minutes

    def commit_boost_change(self, kwargs):
        if self.should_boost != self.boost_active:
            if self.should_boost:
                self.log(f"Boost Activated: Excess: {self.excess_solar}W Battery SOC {self.battery_soc}%")
            else:
                self.log(f"Boost Deactivated: Excess: {self.excess_solar}W Battery SOC: {self.battery_soc}%")

            self.boost_active = self.should_boost
            self.adjust_morning()  # apply new temp

    def adjust_temp(self, kwargs):
        for tstat in self.split_device_list(self.args["thermostats"]):
            self.log(f"Calling Temperature Change: {kwargs['temp']}")
            self.call_service("climate/set_temperature", entity_id=tstat, temperature=kwargs["temp"])

    def occupancy_changed(self, entity, attribute, old, new, kwargs):
        # Re-run adjustment based on current period whenever occupancy changes
        now = datetime.datetime.now().time()
        self.log("Presence changed, calling period adjust")

        if self.time_in_range(self.midnight_adjust, self.morning_adjust_weekday, now):
            self._adjust_period("midnight")
        elif self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, now):
            self._adjust_period("morning")
        else:
            self._adjust_period("night")

    def time_in_range(self, start, end, x):
        if start <= end:
            return start <= x <= end
        else:
            return start <= x or x <= end

    def adjust_morning(self, *args, **kwargs):
        self._adjust_period("morning", force=kwargs.get("force", False))

    def adjust_night(self, *args, **kwargs):
        self._adjust_period("night", force=kwargs.get("force", False))

    def adjust_midnight(self, *args, **kwargs):
        self._adjust_period("midnight", force=kwargs.get("force", False))

    def _adjust_period(self, label, force=False):
        tracker_state = self.get_state(self.args["device_tracker"])
        mode = self.get_state("sensor.thermostat_operating_mode").lower()

        occupied = tracker_state == "home" or force

        if mode == "off":
            return

        # Set unoccupied if grid outage
        if not self.grid_online():
            if mode == "heat":
                temp = self.args["heat_unoccupied"]
            else:  # cool
                temp = self.args["cool_unoccupied"]
            self.log(f"Grid offline, forcing unoccupied temp: {temp} ({mode})")
            self.run_in(self.adjust_temp, 1, temp=temp)
            return

        if mode == "heat":
            temp = self.args[f"heat_{label}"] if occupied else self.args["heat_unoccupied"]

        # Handle cool mode, including boost mode for occupied and unoccupied
        elif mode == "cool":
            if self.boost_active and label == "morning":
                if occupied:
                    temp = int(self.args[f"cool_{label}"]) - int(self.args.get("cool_boost_offset"))
                else:
                    temp = int(self.args["cool_unoccupied"]) - int(self.args.get("cool_boost_unoccupied_offset"))
            else:
                temp = self.args[f"cool_{label}"] if occupied else self.args["cool_unoccupied"]

        self.log(f"Adjust period: '{mode}_{label if occupied else 'unoccupied'}' Mode: '{mode}' Temperature: '{temp}' Boost: '{self.boost_active}'")
        self.run_in(self.adjust_temp, 1, temp=temp)

    # API-compliant wrappers
    # We always force the change if called via API (bypassing occupancy requirement)
    def api_adjust_morning(self, *args, **kwargs):
        self.adjust_morning(force=True)
        return "OK", 200

    def api_adjust_night(self, *args, **kwargs):
        self.adjust_night(force=True)
        self.run_in(lambda kwargs: self.adjust_midnight(force=True), 3600)
        self.log("Scheduled 'midnight' change 1 hour from now")
        return "OK", 200

    def api_adjust_midnight(self, *args, **kwargs):
        self.adjust_midnight(force=True)
        return "OK", 200
