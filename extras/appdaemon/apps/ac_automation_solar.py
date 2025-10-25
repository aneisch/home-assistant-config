import appdaemon.plugins.hass.hassapi as hass
import datetime
#from datetime import timedelta

class AutoAdjust(hass.Hass):
    def initialize(self):
        # Register proper API endpoint wrappers
        self.register_endpoint(self.api_adjust_morning, "adjust_morning")
        self.register_endpoint(self.api_adjust_night, "adjust_night")
        self.register_endpoint(self.api_adjust_midnight, "adjust_midnight")
        self.register_endpoint(self.api_evaluate_now, "evaluate_now")

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
        #self.run_daily(self.adjust_midnight, self.midnight_adjust, constrain_input_boolean="input_boolean.guest_mode,off")
        self.run_daily(self.adjust_midnight, self.midnight_adjust)

        # Debounce window and boost status
        self.boost_active = None
        self.should_boost = None
        self.boost_debounce_handle = None
        self.midnight_scheduled_handle = None

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

    def parse_offset(self, offset_str):
        """Parses HH:MM:SS (with optional '-') into seconds."""
        sign = -1 if offset_str.startswith("-") else 1
        h, m, s = [int(x) for x in offset_str.strip("-").split(":")]
        return sign * (h * 3600 + m * 60 + s)

    def get_sunset_today(self):
        now = datetime.datetime.now()
        next_sunset = self.sunset()  # always returns the next one (could be tomorrow)
        prev_sunrise = self.sunrise()  # the most recent sunrise

        # If the next sunset is more than 12h away, it's likely tomorrow's
        if (next_sunset - now).total_seconds() > 12 * 3600:
            # Compute yesterday's by subtracting one day
            return next_sunset - datetime.timedelta(days=1)
        return next_sunset

    def evaluate_boost_conditions(self):
        now = datetime.datetime.now()
        # Read offsets from args
        start_offset_str = self.args.get("cooldown_window_start_offset", "-02:00:00")
        end_offset_str   = self.args.get("cooldown_window_end_offset", "-00:30:00")

        try:
            start_offset = self.parse_offset(start_offset_str)
            end_offset   = self.parse_offset(end_offset_str)
        except Exception as e:
            self.log(f"Invalid offset format: {e} {start_offset_str}, {end_offset_str}", level="WARNING")
            return

        # Get today's sunset
        sunset = self.get_sunset_today()

        # Apply offsets (still datetime)
        start = sunset + datetime.timedelta(seconds=start_offset)
        end   = sunset + datetime.timedelta(seconds=end_offset)
        self.log(f"{now} - {start} - {end}")

        # Check EV Charging
        try:
            ev_is_charging = self.get_state("switch.emporia_charger", attribute='status') == "Charging"
        except:
            ev_is_charging = False

        # Rule 0.1: Boost only allowed within window. If active and window ends → deactivate immediately.
        # If grid outage --> Deactivate boost immediately 
        # If EV charging --> Deactivate immediately
        if not (start <= now <= end) or not self.grid_online() or ev_is_charging:
            self.log(f"Rule 0.1 - In Window: {start <= now <= end} - Grid On: {self.grid_online()} - EV Charging: {ev_is_charging}")
            if self.boost_active:
                self.should_boost = False
                self.commit_boost_change({})
                self.log("Boost deactivated: outside allowed window, grid offline, or EV charging")
            return

        # Rule 0.2: Allow disabling the feature by boolean
        if self.get_state("input_boolean.ac_boost_feature_evaluation") == "off":
            self.log("Rule 0.2")
            if self.boost_debounce_handle:
                self.cancel_timer(self.boost_debounce_handle)
                self.boost_debounce_handle = None
                self.log("Boost deactivation cancelled (manual override)")
            return

        try:
            solar_power = float(self.get_state("sensor.solark_sol_ark_solar_power") or 0)
            load_power = float(self.get_state("sensor.solark_sol_ark_load_power") or 0)
            grid_power = float(self.get_state("sensor.solark_sol_ark_grid_ct_power") or 0)
            ac_running = self.get_state("sensor.thermostat_state") == "Cooling"
            ac_power = int(float(self.get_state("sensor.ac_compressor_power")) +
                        float(self.get_state("sensor.attic_hvac_power")))
            battery_soc = float(self.get_state("sensor.solark_sol_ark_battery_soc") or 0)
        except (TypeError, ValueError):
            self.log("Invalid sensor data", level="WARNING")
            return

        # Adjust load depending on AC state
        if grid_power < -500:  # exporting
            self.log("Rule 1")
            if ac_running:
                self.log("Rule 1.1")
                # Rule 4: Don’t let AC running disable boost → ignore AC load when already running
                adjusted_load = max(0, load_power - ac_power)
            else:
                self.log("Rule 1.2")
                # If AC is off, test whether solar can also handle turning it on
                adjusted_load = load_power + 4500
            excess_solar = solar_power - adjusted_load
        else:
            self.log("Rule 2")
            adjusted_load = 0
            excess_solar = 0

        self.excess_solar = excess_solar
        self.battery_soc = battery_soc

        # Rule 3: Only activate if there is enough solar + buffer threshold
        # solar_threshold = float(self.args["solar_boost_threshold"])
        # battery_threshold = float(self.args["battery_boost_threshold"])

        # We need to produce at least what the AC is currently drawing to be eligible for boost
        required_solar = ac_power + float(self.args["solar_boost_threshold"])

        eligible = (
            solar_power >= required_solar and
            excess_solar > float(self.args["solar_boost_threshold"]) and
            battery_soc >= float(self.args["battery_boost_threshold"])
        )

        self.log(f"Boost Evaluation Result: {eligible} - Solar: {solar_power}W - Load: {load_power}W - Adjusted Load: {adjusted_load}W - Calculated Excess: {excess_solar}W - Battery SOC {battery_soc}%", level="INFO")

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
                self.boost_debounce_handle = self.run_in(self.commit_boost_change, 150)  # 2.5 minutes

    def commit_boost_change(self, kwargs):
        self.log("evaluating")
        #if self.should_boost != self.boost_active:
        if self.should_boost:
            self.log(f"Boost Activated")
            self.set_state("input_boolean.ac_is_boosting", state="on")
        else:
            self.log(f"Boost Deactivated")
            self.set_state("input_boolean.ac_is_boosting", state="off")
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
        if self.get_state("input_boolean.goodnight") == "off":
            self._adjust_period("night", force=kwargs.get("force", False))
        else:
            self.log("Not transitioning to 'night' due to input_boolean.goodnight == on")

    def adjust_midnight(self, *args, **kwargs):
        self._adjust_period("midnight", force=kwargs.get("force", False))

    def _adjust_period(self, label, force=False):
        tracker_state = self.get_state(self.args["device_tracker"])
        mode = self.get_state("sensor.thermostat_operating_mode").lower()
        guest_mode = self.get_state("input_boolean.guest_mode") == "on"
        occupied = tracker_state == "home" or guest_mode or force

        if mode == "off":
            return

        # If grid is offline, always fall back to unoccupied temps
        if not self.grid_online():
            if mode == "heat":
                temp = self.args.get("guest_heat_unoccupied" if guest_mode else "heat_unoccupied")
            else:
                temp = self.args.get("guest_cool_unoccupied" if guest_mode else "cool_unoccupied")
            self.log(f"Grid offline, forcing unoccupied temp: {temp} ({mode})")
            self.run_in(self.adjust_temp, 1, temp=temp)
            return

        # --- HEAT MODE ---
        if mode == "heat":
            prefix = "guest_heat_" if guest_mode else "heat_"
            if occupied:
                temp = self.args.get(f"{prefix}{label}", self.args[f"heat_{label}"])
            else:
                temp = self.args.get(f"{prefix}unoccupied", self.args["heat_unoccupied"])

        # --- COOL MODE ---
        elif mode == "cool":
            prefix = "guest_cool_" if guest_mode else "cool_"

            if self.boost_active and label == "morning":
                if occupied:
                    base_temp = self.args.get(f"{prefix}{label}", self.args[f"cool_{label}"])
                    if guest_mode:
                        temp = int(base_temp) - int(self.args.get("cool_boost_offset_guest", 0))
                    else:
                        temp = int(base_temp) - int(self.args.get("cool_boost_offset", 0))
                else:
                    base_temp = self.args.get(f"{prefix}unoccupied", self.args["cool_unoccupied"])
                    temp = int(base_temp) - int(self.args.get("cool_boost_unoccupied_offset", 0))
            else:
                temp = self.args.get(f"{prefix}{label}", self.args[f"cool_{label}"]) if occupied \
                    else self.args.get(f"{prefix}unoccupied", self.args["cool_unoccupied"])

        self.log(
            f"Adjust period: '{mode}_{label if occupied else 'unoccupied'}' "
            f"Mode: '{mode}' Temp: '{temp}' Boost: '{self.boost_active}' Guest: {guest_mode}"
        )
        self.run_in(self.adjust_temp, 1, temp=temp)

    # API-compliant wrappers
    # We always force the change if called via API (bypassing occupancy requirement)
    def api_adjust_morning(self, *args, **kwargs):
        self.adjust_morning(force=True)
        return "OK", 200

    def api_adjust_night(self, *args, **kwargs):
        self.adjust_night(force=True)

        # Cancel any existing scheduled midnight
        if self.midnight_scheduled_handle:
            try:
                self.cancel_timer(self.midnight_scheduled_handle)
                self.log("Cancelled previous scheduled 'midnight' change")
            except Exception as e:
                self.log(f"Error cancelling previous timer: {e}", level="WARNING")
            self.midnight_scheduled_handle = None

        # Schedule new midnight adjustment
        self.midnight_scheduled_handle = self.run_in(
            lambda kwargs: self.adjust_midnight(force=True), 3600
        )
        self.log("Scheduled 'midnight' change 1 hour from now")
        return "OK", 200

    def api_adjust_midnight(self, *args, **kwargs):
        self.adjust_midnight(force=True)
        return "OK", 200

    def api_evaluate_now(self, *args, **kwargs):
        """Force re-evaluation of current occupancy/time period conditions."""
        now = datetime.datetime.now().time()
        self.log("API: Forced evaluation of current period")

        if self.time_in_range(self.midnight_adjust, self.morning_adjust_weekday, now):
            self._adjust_period("midnight", force=True)
        elif self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, now):
            self._adjust_period("morning", force=True)
        else:
            self._adjust_period("night", force=True)

        return "OK", 200