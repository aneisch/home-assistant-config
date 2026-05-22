import appdaemon.plugins.hass.hassapi as hass
import datetime

class SolarEVCharger(hass.Hass):
    def initialize(self):
        # Configurable constants
        self.min_amps = int(self.args.get("min_amps", 6))
        self.max_amps = int(self.args.get("max_amps", 40))
        self.volts = int(self.args.get("volts", 240))
        self.min_home_soc = int(self.args.get("home_battery_min_soc", 90))
        self.buffer_watts = int(self.args.get("buffer_watts", 250))
        self.cooldown = int(self.args.get("cooldown", 10)) 
        self.disable_timeout = int(self.args.get("disable_timeout", 600)) 

        # State
        self.eval_locked = False
        self.insufficient_solar_since = None
        self.insufficient_disabled = False
        self.notify_handler = None
        self.emporia_prior_status = None

        # Entities
        self.entities = {
            # Shared Core Entities
            "home_soc": "sensor.solark_sol_ark_battery_soc",
            "ev_prioritization": "input_boolean.ev_charge_prioritize_vehicle_over_home_battery",
            "solar": "sensor.solark_sol_ark_solar_power",
            "load": "sensor.solark_sol_ark_load_power",
            "override_boolean": "input_boolean.ev_charge_override",
            "grid_status": "binary_sensor.solark_sol_ark_grid_connected_status",
            "charger_switch": "switch.emporia_charger",
            
            # Master Rate Adjuster (Controls Emporia via your existing setup)
            "charge_rate": "input_number.tesla_charge_rate_master",
            
            # Mode Gate Toggle Helper
            "guest_mode": "input_boolean.ev_charge_guest_mode",
            
            # Tesla-Specific Entities (Ignored when guest_mode is ON)
            "charge_limit": "number.tesla_ble_charging_limit",
            "target_soc": "input_number.tesla_solar_target_soc_limit",
        }

        # Track fundamental state changes
        for sensor in ["solar", "home_soc", "load", "target_soc", "grid_status", "guest_mode"]:
            self.listen_state(self.evaluate_charging, self.entities[sensor])

        self.log(f"SolarEVCharger initialized. Min Home SOC: {self.min_home_soc}%, Buffer: {self.buffer_watts}W")

    def evaluate_charging(self, entity, attribute, old, new, kwargs):
        # 1. IMMEDIATE GRID KILL
        if entity == self.entities["grid_status"]:
            if new == "off":
                self.emporia_prior_status = self.get_state(self.entities["charger_switch"])
                self.turn_off(self.entities["charger_switch"])
                self.log("CRITICAL: Grid outage! EV charger killed immediately.")
                return
            if old == "off" and new == "on":
                if self.emporia_prior_status == "on":
                    self.turn_on(self.entities["charger_switch"])
                    self.log("INFO: Grid restored. Resuming previous charger state.")
                return

        if self.get_state(self.entities["grid_status"]) == "off":
            return

        # 2. OVERRIDE & CONNECTION CHECKS
        if self.get_state(self.entities["override_boolean"]) == "on":
            self.log("DEBUG: Evaluation skipped (Manual Override ON)", level="DEBUG")
            self.insufficient_solar_since = None
            self.insufficient_disabled = False
            return

        icon = self.get_state(self.entities["charger_switch"], attribute='icon_name')
        if icon == "CarNotConnected":
            self.log("DEBUG: No vehicle connected.", level="DEBUG")
            self.eval_locked = False
            self.insufficient_solar_since = None
            self.insufficient_disabled = False
            return

        if self.eval_locked:
            return

        # 3. DATA GATHERING
        try:
            guest_mode = self.get_state(self.entities["guest_mode"])
            home_soc = int(float(self.get_state(self.entities["home_soc"])))
            solar_watts = int(float(self.get_state(self.entities["solar"])))
            load_watts = int(float(self.get_state(self.entities["load"])))
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
            ev_prioritization = self.get_state(self.entities["ev_prioritization"])
            
            if guest_mode == "on":
                target_soc = "N/A (Guest Mode)"
            else:
                target_soc = int(float(self.get_state(self.entities["target_soc"])))
                
        except Exception as e:
            self.log(f"WARNING: Skipping eval due to data error: {e}")
            return

        # 4. CALCULATIONS
        charger_state = self.get_state(self.entities["charger_switch"])
        ev_power = (present_rate * self.volts) if charger_state == "on" else 0
        house_load_only = load_watts - ev_power 
        modified_buffer_watts = self.buffer_watts + 2000 if home_soc < 99 else self.buffer_watts
        excess_watts = max(0, solar_watts - house_load_only - modified_buffer_watts)
        target_amps = excess_watts // self.volts

        # 5. DEFICIT LOGIC
        battery_blocked = (ev_prioritization == "off" and home_soc < self.min_home_soc) or \
                          (ev_prioritization == "on" and home_soc < 50)

        if target_amps < self.min_amps or battery_blocked:
            if self.insufficient_solar_since is None:
                self.insufficient_solar_since = datetime.datetime.now()
            
            elapsed = (datetime.datetime.now() - self.insufficient_solar_since).total_seconds()

            if elapsed >= self.disable_timeout or (solar_watts < 100) or battery_blocked:
                if not self.insufficient_disabled:
                    mode_str = "GUEST" if guest_mode == "on" else "TESLA"
                    if solar_watts < 100:
                        self.log(f"STOP [{mode_str}]: No solar. Executing deficit routine.")
                    elif battery_blocked:
                        self.log(f"STOP [{mode_str}]: Home SOC too low. Executing deficit routine.")
                    elif elapsed >= self.disable_timeout:
                        self.log(f"STOP [{mode_str}]: Deficit timeout expired, lasted {int(elapsed)}s. Executing deficit routine.")
                    self.insufficient_disabled = True
                
                self.safe_set_rate(self.min_amps, disable=True, guest_mode=(guest_mode == "on"))
            else:
                self.log(f"THROTTLE: Deficit detected. {home_soc}% SOC, {solar_watts}W Solar. Dropping to {self.min_amps}A. (Shutdown in {int(self.disable_timeout - elapsed)}s)")
                self.safe_set_rate(self.min_amps, disable=False, guest_mode=(guest_mode == "on"))
        else:
            # 6. SURPLUS LOGIC
            self.insufficient_solar_since = None
            self.insufficient_disabled = False
            final_amps = min(self.max_amps, int(target_amps))
            
            self.log(f"Home: {home_soc}% | Solar: {solar_watts}W | House: {house_load_only}W | EV Target:{target_soc} | Set: {final_amps}A")
            self.safe_set_rate(final_amps, disable=False, guest_mode=(guest_mode == "on"))

    def safe_set_rate(self, amps, disable=False, guest_mode=False):
        if self.notify_handler and self.info_timer(self.notify_handler):
            self.cancel_timer(self.notify_handler)
        
        try:
            charger_state = self.get_state(self.entities["charger_switch"])
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
            
            if not guest_mode:
                present_limit = int(float(self.get_state(self.entities["charge_limit"])))
                target_soc = int(float(self.get_state(self.entities["target_soc"])))
        except Exception as e:
            self.log(f"WARNING: safe_set_rate skipped, state fetch failed: {e}")
            return

        if disable:
            changes_made = False

            if guest_mode:
                # GUEST DEFICIT PATH: Completely turn off the charger box to prevent late-night grid draw
                if charger_state != "off":
                    self.turn_off(self.entities["charger_switch"])
                    self.log("FORCE [Guest]: Turning Emporia Station OFF (No Solar/Night).")
                    changes_made = True
                if present_rate != self.min_amps:
                    self.call_service("input_number/set_value", entity_id=self.entities["charge_rate"], value=self.min_amps)
                    changes_made = True
            else:
                # TESLA DEFICIT PATH: Clamp car SoC via BLE to 50%, leave station hardware active
                if present_limit != 50:
                    self.turn_off("automation.tesla_charge_limit_change_notice")
                    self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=50)
                    self.notify_handler = self.run_in(self._enable_notice, 60)
                    self.log("FORCE [Tesla]: Clamping Tesla charge limit to 50%")
                    changes_made = True
                    
                if present_rate != self.min_amps:
                    self.call_service("input_number/set_value", entity_id=self.entities["charge_rate"], value=self.min_amps)
                    self.log(f"FORCE [Tesla]: Setting master charge rate to minimum ({self.min_amps}A).")
                    changes_made = True

            # Exit without evaluation lock if states match target parameters
            if not changes_made:
                return
        else:
            # DAYTIME/SURPLUS LOGIC
            if charger_state == "off":
                self.turn_on(self.entities["charger_switch"])
                self.log("Emporia Charger turned ON")
                
                # Only spin up Tesla native BLE wake/charge triggers if guest mode is off
                if not guest_mode:
                    self.call_service(
                        "mqtt/publish",
                        topic="tesla_ble/5YJSA1E5XMF436975/charging",
                        payload="start"
                    )
                    self.log("Tesla commanded to start charging via BLE")
            
            # BOTH MODES: Modulate charge current via the master rate entity
            if present_rate != amps:
                self.call_service("input_number/set_value", entity_id=self.entities["charge_rate"], value=amps)

            if not guest_mode:
                # Tesla-specific internal target updates
                if present_limit != target_soc:
                    self.turn_off("automation.tesla_charge_limit_change_notice")
                    self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=target_soc)
                    self.notify_handler = self.run_in(self._enable_notice, 60)

        self.eval_locked = True
        self.run_in(self._unlock_eval, self.cooldown)

    def _unlock_eval(self, kwargs):
        self.eval_locked = False

    def _enable_notice(self, kwargs):
        self.turn_on("automation.tesla_charge_limit_change_notice")