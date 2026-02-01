import appdaemon.plugins.hass.hassapi as hass
import datetime

class SolarEVCharger(hass.Hass):
    def initialize(self):
        # Configurable constants
        self.min_amps = int(self.args.get("min_amps", 6))
        self.max_amps = int(self.args.get("max_amps", 40))
        self.volts = int(self.args.get("volts", 240))
        self.min_home_soc = int(self.args.get("home_battery_min_soc", 98))
        self.buffer_watts = int(self.args.get("buffer_watts", 250))
        self.cooldown = int(self.args.get("cooldown", 15)) 
        self.disable_timeout = int(self.args.get("disable_timeout", 600)) 

        # State
        self.eval_locked = False
        self.insufficient_solar_since = None
        self.insufficient_solar_disabled = False
        self.notify_handler = None
        self.emporia_prior_status = None

        # Entities
        self.entities = {
            "home_soc": "sensor.solark_sol_ark_battery_soc",
            "ev_prioritization": "input_boolean.ev_charge_prioritize_vehicle_over_home_battery",
            "solar": "sensor.solark_sol_ark_solar_power",
            "load": "sensor.solark_sol_ark_load_power",
            "charge_rate": "input_number.tesla_charge_rate_master",
            "charge_limit": "number.tesla_ble_charging_limit",
            "target_soc": "input_number.tesla_solar_target_soc_limit",
            "vehicle_soc": "sensor.tesla_battery_level",
            "override_boolean": "input_boolean.ev_charge_override",
            "grid_status": "binary_sensor.solark_sol_ark_grid_connected_status"
        }

        for sensor in ["solar", "home_soc", "load", "target_soc", "grid_status"]:
            self.listen_state(self.evaluate_charging, self.entities[sensor])

        self.log(f"SolarEVCharger initialized. Min Home SOC: {self.min_home_soc}%, Buffer: {self.buffer_watts}W")

    def evaluate_charging(self, entity, attribute, old, new, kwargs):
        # 1. IMMEDIATE GRID KILL
        if entity == self.entities["grid_status"]:
            if new == "off":
                self.emporia_prior_status = self.get_state("switch.emporia_charger")
                self.turn_off("switch.emporia_charger")
                self.log("CRITICAL: Grid outage! EV charger killed immediately.")
                return
            if old == "off" and new == "on":
                if self.emporia_prior_status == "on":
                    self.turn_on("switch.emporia_charger")
                    self.log("INFO: Grid restored. Resuming previous charger state.")
                return

        if self.get_state(self.entities["grid_status"]) == "off":
            return

        # 2. OVERRIDE & CONNECTION CHECKS
        if self.get_state(self.entities["override_boolean"]) == "on":
            self.log("DEBUG: Evaluation skipped (Manual Override ON)", level="DEBUG")
            self.insufficient_solar_since = None
            self.insufficient_solar_disabled = False
            return

        icon = self.get_state("switch.emporia_charger", attribute='icon_name')
        if icon == "CarNotConnected":
            self.log("DEBUG: No vehicle connected.", level="DEBUG")
            self.eval_locked = False
            self.insufficient_solar_since = None
            self.insufficient_solar_disabled = False
            return

        if self.eval_locked:
            return

        # 3. DATA GATHERING
        try:
            home_soc = int(float(self.get_state(self.entities["home_soc"])))
            solar_watts = int(float(self.get_state(self.entities["solar"])))
            load_watts = int(float(self.get_state(self.entities["load"])))
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
            ev_prioritization = self.get_state(self.entities["ev_prioritization"])
            vehicle_soc = int(float(self.get_state(self.entities["vehicle_soc"])))
            target_soc = int(float(self.get_state(self.entities["target_soc"])))
        except Exception as e:
            self.log(f"WARNING: Skipping eval due to data error: {e}")
            return

        # 4. CALCULATIONS
        ev_power = present_rate * self.volts
        # Non-EV load is current load minus what the car is drawing
        house_load_only = load_watts - ev_power
        excess_watts = max(0, solar_watts - house_load_only - self.buffer_watts)
        target_amps = excess_watts // self.volts

        # 5. DEFICIT LOGIC
        # Priority logic: EV > Home if prioritization is ON and home > 50%
        battery_blocked = (ev_prioritization == "off" and home_soc < self.min_home_soc) or \
                          (ev_prioritization == "on" and home_soc < 50)

        if battery_blocked or target_amps < self.min_amps:
            if self.insufficient_solar_since is None:
                self.insufficient_solar_since = datetime.datetime.now()
                self.log(f"NOTICE: Solar/Battery deficit. Starting {self.disable_timeout}s countdown.")
            
            elapsed = (datetime.datetime.now() - self.insufficient_solar_since).total_seconds()

            # If disable_timeout exceeded OR zero solar
            if elapsed >= self.disable_timeout or (solar_watts == 0):
                if self.insufficient_solar_disabled == False:
                    self.log(f"STOP: Deficit timeout expired, lasted {int(elapsed)}s. Setting limit to 50%.")
                    self.safe_set_rate(self.min_amps, disable=True)
                    self.insufficient_solar_disabled = True
                else:
                    return
            else:
                self.log(f"THROTTLE: Deficit detected. {home_soc}% SOC, {solar_watts}W Solar. Dropping to {self.min_amps}A. (Shutdown in {int(self.disable_timeout - elapsed)}s)")
                self.safe_set_rate(self.min_amps, disable=False)
        else:
            # 6. SURPLUS LOGIC
            self.insufficient_solar_since = None
            self.insufficient_solar_disabled = False
            final_amps = min(self.max_amps, int(target_amps))
            
            self.log(f"Home: {home_soc}% | Solar: {solar_watts}W | House: {house_load_only}W | EV: {vehicle_soc}% -> {target_soc}% | Set: {final_amps}A")
            self.safe_set_rate(final_amps, disable=False)

    def safe_set_rate(self, amps, disable=False):
        if self.notify_handler and self.info_timer(self.notify_handler):
            self.cancel_timer(self.notify_handler)
        
        try:
            present_limit = int(float(self.get_state(self.entities["charge_limit"])))
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
            target_soc = int(float(self.get_state(self.entities["target_soc"])))
        except: return

        if disable:
            if present_limit != 50:
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=50)
                self.notify_handler = self.run_in(self._enable_notice, 30)
            if present_rate != self.min_amps:
                self.call_service("input_number/set_value", entity_id=self.entities["charge_rate"], value=self.min_amps)
        else:
            if self.get_state("switch.emporia_charger") == "off":
                self.turn_on("switch.emporia_charger")
                self.log("Emporia Charger turned ON")
            
            if present_limit != target_soc:
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=target_soc)
                self.notify_handler = self.run_in(self._enable_notice, 30)
            
            if present_rate != amps:
                self.call_service("input_number/set_value", entity_id=self.entities["charge_rate"], value=amps)

        self.eval_locked = True
        self.run_in(self._unlock_eval, self.cooldown)

    def _unlock_eval(self, kwargs):
        self.eval_locked = False

    def _enable_notice(self, kwargs):
        self.turn_on("automation.tesla_charge_limit_change_notice")