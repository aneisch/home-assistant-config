import appdaemon.plugins.hass.hassapi as hass
import datetime

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
        self.run_daily(self.adjust_midnight, self.midnight_adjust)

        # Debounce window and boost status
        self.boost_active = self.get_state("input_boolean.ac_is_boosting") == "on"
        self.should_boost = self.boost_active
        self.boost_debounce_handle = None
        self.midnight_scheduled_handle = None

        # Last period applied (morning/night/midnight); None until first adjustment
        self.period = None

        # Listen to solar, load, SOC changes (update -- only listen for solar changes. 5s tick)
        self.listen_state(self.solar_change_callback, "sensor.solark_sol_ark_solar_power")

        # Presence detection
        if "device_tracker" in self.args:
            self.listen_state(self.occupancy_changed, self.args["device_tracker"])

        if "cool_boost_entity" in self.args:
            self.listen_state(self.slider_changed_callback, self.args["cool_boost_entity"])

    def slider_changed_callback(self, entity, attribute, old, new, kwargs):
        self.log(f"Slider changed to {new}, updating temperature settings.")
        self._adjust_period(self.current_period())

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

        # If the next sunset is more than 12h away, it's likely tomorrow's
        if (next_sunset - now).total_seconds() > 12 * 3600:
            return next_sunset - datetime.timedelta(days=1)
        return next_sunset

    def evaluate_boost_conditions(self):
        now = datetime.datetime.now()
        
        # Determine occupancy to select the appropriate start offset key
        tracker_state = self.get_state(self.args["device_tracker"]) if "device_tracker" in self.args else "home"
        occupied = tracker_state == "home"

        if occupied:
            start_offset_str = self.args.get("cooldown_window_start_offset", "-02:00:00")
        else:
            start_offset_str = self.args.get("cooldown_window_start_offset_unoccupied", "-02:00:00")


        end_offset_str = self.args.get("cooldown_window_end_offset", "-00:30:00")
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
        self.log(f"Using {'occupied' if occupied else 'unoccupied'} boost schedule - {now} - {start} - {end}")

        # Check EV Charging
        try:
            ev_is_charging = float(self.get_state("sensor.emporia_view_tesla_charger_power")) > 10
        except:
            ev_is_charging = False

        # Rule 0.1: Boost only allowed within window. If active and window ends → deactivate immediately.
        # If grid outage --> Deactivate boost immediately 
        if not (start <= now <= end) or not self.grid_online():
            self.deactivate_boost_now("outside allowed window or grid offline")
            return

        # Rule 0.2: Allow disabling the feature by boolean → end any active boost immediately
        if self.get_state("input_boolean.ac_boost_feature_evaluation") == "off":
            self.deactivate_boost_now("feature evaluation disabled")
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
        if grid_power < -100:  # exporting: Make sure we truly have excess
            if ac_running:
                # Rule 4: Don’t let AC running disable boost → ignore AC load when already running
                adjusted_load = max(0, load_power - ac_power)
            else:
                # If AC is off, test whether solar can also handle turning it on
                adjusted_load = load_power + 4500
            excess_solar = solar_power - adjusted_load
        else:
            adjusted_load = load_power
            excess_solar = 0

        self.excess_solar = excess_solar
        self.battery_soc = battery_soc

        # Rule 3: Evaluate eligibility with late-afternoon battery sustaining check
        required_solar = ac_power + float(self.args["solar_boost_threshold"])
        
        # Standard rules required to INITIATE a brand new boost
        solar_ok = (
            solar_power >= required_solar and
            excess_solar > float(self.args["solar_boost_threshold"])
        )
        battery_ok = battery_soc >= float(self.args["battery_boost_threshold"])

        if self.boost_active:
            # SUSTAIN BOOST: Once active, allow battery drainage down to 97% at the end of the day
            eligible = battery_soc >= 97.0
            if not eligible:
                self.log(f"Boost ending: Battery SOC ({battery_soc}%) dropped below 97% safety limit.")
        else:
            # INITIATE BOOST: Standard solar and battery rules apply to trigger it on
            eligible = solar_ok and battery_ok

        self.log(f"Boost Evaluation Result: {eligible} - Solar: {solar_power}W - Load: {load_power}W - Adjusted Load: {adjusted_load}W - Calculated Excess: {excess_solar}W - Battery SOC {battery_soc}%", level="INFO")

        if eligible != self.should_boost:
            self.log(f"Eligibility changed --> {eligible} (was {self.should_boost})", level="INFO")
            self.should_boost = eligible

            # Cancel any pending deactivation timer
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

    def deactivate_boost_now(self, reason):
        if self.boost_debounce_handle:
            self.cancel_timer(self.boost_debounce_handle)
            self.boost_debounce_handle = None
        self.should_boost = False
        if self.boost_active:
            self.commit_boost_change({})
            self.log(f"Boost deactivated: {reason}")

    def commit_boost_change(self, kwargs):
        self.boost_debounce_handle = None
        if self.should_boost:
            self.log(f"Boost Activated")
            self.turn_on("input_boolean.ac_is_boosting")
        else:
            self.log(f"Boost Deactivated")
            self.turn_off("input_boolean.ac_is_boosting")
        self.boost_active = self.should_boost
        self._adjust_period(self.current_period())  # apply new temp

    def adjust_temp(self, kwargs):
        for tstat in self.split_device_list(self.args["thermostats"]):
            self.log(f"Calling Temperature Change: {kwargs['temp']}")
            self.call_service("climate/set_temperature", entity_id=tstat, temperature=kwargs["temp"])

    def occupancy_changed(self, entity, attribute, old, new, kwargs):
        # Re-run adjustment based on current period whenever occupancy changes
        self.log("Presence changed, calling period adjust")
        self._adjust_period(self.current_period())

    def current_period(self):
        """Period last applied (respects early API night calls); falls back to the clock."""
        return self.period or self.period_by_clock()

    def period_by_clock(self):
        now = datetime.datetime.now()
        weekend = now.weekday() >= 5
        morning = self.morning_adjust_weekend if weekend else self.morning_adjust_weekday
        night = self.night_adjust_weekend if weekend else self.night_adjust_weekday
        t = now.time()

        if self.time_in_range(self.midnight_adjust, morning, t):
            return "midnight"
        elif self.time_in_range(morning, night, t):
            return "morning"
        return "night"

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
        self.period = label
        tracker_state = self.get_state(self.args["device_tracker"])
        mode = (self.get_state("sensor.thermostat_operating_mode") or "").lower()
        guest_mode = self.get_state("input_boolean.guest_mode") == "on"
        occupied = tracker_state == "home" or guest_mode or force

        if mode not in ("heat", "cool"):
            if mode != "off":
                self.log(f"Unsupported thermostat mode '{mode}', not adjusting", level="WARNING")
            return

        # If grid is offline, always fall back to unoccupied temps
        if not self.grid_online():
            base = f"{mode}_unoccupied"
            temp = self.args.get(f"guest_{base}", self.args[base]) if guest_mode else self.args[base]
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
                cool_boost_entity = self.args.get("cool_boost_entity")
                if cool_boost_entity:
                    try:
                        temp = int(float(self.get_state(cool_boost_entity)))
                    except (TypeError, ValueError) as e:
                        temp = 75
                        self.log(f"Boost slider exception: {e}")

                # Hard code boost temp if not defined by slider
                else:
                    temp = 75

            else:
                temp = self.args.get(f"{prefix}{label}", self.args[f"cool_{label}"]) if occupied \
                    else self.args.get(f"{prefix}unoccupied", self.args["cool_unoccupied"])

        # Actually make the changes
        self.log(
            f"Adjust period: '{mode}_{label if occupied else 'unoccupied'}' "
            f"Mode: '{mode}' Temp: '{temp}' Boost: '{self.boost_active}' Guest: {guest_mode}"
        )
        self.run_in(self.adjust_temp, 1, temp=temp)

    # API-compliant wrappers
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
        self.log("API: Forced evaluation of current period")
        self._adjust_period(self.period_by_clock(), force=True)

        return "OK", 200