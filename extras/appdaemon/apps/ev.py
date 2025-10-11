import appdaemon.plugins.hass.hassapi as hass

class SolarEVCharger(hass.Hass):
    def initialize(self):
        # Configurable constants
        self.min_amps = int(self.args.get("min_amps", 6))
        self.max_amps = int(self.args.get("max_amps", 40))
        self.volts = int(self.args.get("volts", 240))
        self.min_home_soc = int(self.args.get("home_battery_min_soc", 90))
        self.buffer_watts = int(self.args.get("buffer_watts", 500))
        self.cooldown = int(self.args.get("cooldown", 15))  # seconds

        # State
        self.eval_locked = False
        self.notify_handler = None

        # Entities
        self.entities = {
            "home_soc": "sensor.solark_sol_ark_battery_soc",
            "solar": "sensor.solark_sol_ark_solar_power",
            "load": "sensor.solark_sol_ark_load_power",
            "charge_rate": "input_number.tesla_charge_rate_master",
            "charge_limit": "number.tesla_ble_charging_limit",
            "target_soc": "input_number.tesla_solar_target_soc_limit",
            "vehicle_soc": "sensor.tesla_battery_level",
            "override_boolean": "input_boolean.ev_charge_override",
            "grid_status": "binary_sensor.solark_sol_ark_grid_connected_status"
        }

        # Listen to changes
        for sensor in ["solar", "home_soc", "load", "target_soc", "grid_status"]:
            self.listen_state(self.evaluate_charging, self.entities[sensor])

        # Safe startup
        self.set_charge_rate(self.min_amps, disable=True)
        self.log("SolarEVCharger initialized")

    def evaluate_charging(self, entity, attribute, old, new, kwargs):
        #details = self.get_state("person", namespace=None, copy=True)
        #self.log(any(state['state'] == 'home' for state in details.values()))
        #self.log("Eval called")
        # Disable all charging if grid outage
        if entity == "binary_sensor.solark_sol_ark_grid_connected_status":
            if old == "on" and new == "off":
                self.turn_off("switch.emporia_charger")
                self.log("Turned off switch.emporia_charger due to grid outage")
            # if old == "off" and new == "on":
            #     self.turn_off("switch.emporia_charger")
            #     self.log("Turned on switch.emporia_charger due to grid outage")

        # Allow manual override
        if self.get_state(self.entities["override_boolean"]) == "on":
            self.log("Overridden")

            return

        if self.get_state("switch.emporia_charger", attribute='icon_name') == "CarNotConnected":
            self.log("No Vehicle Connected")
            return

        if self.eval_locked:
            self.log("Eval Locked")
            return

        try:
            home_soc = int(float(self.get_state(self.entities["home_soc"])))
            vehicle_soc = int(float(self.get_state(self.entities["vehicle_soc"])))
            solar_watts = int(float(self.get_state(self.entities["solar"])))
            load_watts = int(float(self.get_state(self.entities["load"])))
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
            target_soc = int(float(self.get_state(self.entities["target_soc"])))
        except (TypeError, ValueError) as e:
            self.log(f"Invalid sensor reading: {e}", level="WARNING")
            return

        # Block charging if battery too low or vehicle full
        if home_soc < self.min_home_soc:
            self.set_charge_rate(self.min_amps, disable=True)
            return

        # Don't bother evaluating if we are charged already
        if vehicle_soc >= target_soc:
            self.log("Already fully charged")
            return

        # Compute available amps from solar
        ev_power = present_rate * self.volts
        excess_watts = max(0, solar_watts - (load_watts - ev_power) - self.buffer_watts)
        target_amps = max(self.min_amps, min(self.max_amps, excess_watts // self.volts))

        self.log(f"Home: {home_soc}% -- Solar: {solar_watts}W -- Load: {load_watts}W -- Vehicle: {vehicle_soc} --> {target_soc} -- Rate: {present_rate} --> {target_amps}")

        if target_amps > self.min_amps:
            self.set_charge_rate(target_amps)
        else:
            self.set_charge_rate(self.min_amps, disable=True)

    def _enable_notice(self, kwargs):
        self.turn_on("automation.tesla_charge_limit_change_notice")

    def _unlock_eval(self, kwargs):
        self.eval_locked = False

    def set_charge_rate(self, amps, disable=False):
        # Cancel any pending notifications
        if self.notify_handler and self.info_timer(self.notify_handler):
            self.cancel_timer(self.notify_handler)
        self.notify_handler = None

        try:
            present_limit = int(float(self.get_state(self.entities["charge_limit"])))
            present_rate = int(float(self.get_state(self.entities["charge_rate"])))
        except (TypeError, ValueError):
            present_limit = 0
            present_rate = 0

        target_soc = int(float(self.get_state(self.entities["target_soc"])))

        if disable:
            if present_limit != 50 or present_rate != self.min_amps:
                self.log(f"Disabling charging")
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=50)
                self.set_value(self.entities["charge_rate"], self.min_amps)
                self.notify_handler = self.run_in(self._enable_notice, 30)
        else:
            if self.get_state("switch.emporia_charger") == "off":
                self.turn_on("switch.emporia_charger")
                self.log("Turned on switch.emporia_charger")
            if present_rate != amps:
                self.set_value(self.entities["charge_rate"], amps)
                self.log(f"Set charge rate to {amps}A (SOC limit {target_soc}%)")
            if present_limit != target_soc:
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.entities["charge_limit"], value=target_soc)
                self.notify_handler = self.run_in(self._enable_notice, 30)

        # Lock eval during cooldown
        self.eval_locked = True
        self.run_in(self._unlock_eval, self.cooldown)