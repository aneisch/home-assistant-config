import appdaemon.plugins.hass.hassapi as hass

class SolarEVCharger(hass.Hass):

    def initialize(self):
        # Configurable constants from apps.yaml (with defaults if not set)
        self.min_amps = int(self.args.get("min_amps", 6))                # Emporia/Tesla minimum charge rate
        self.max_amps = int(self.args.get("max_amps", 40))               # Emporia/Tesla max charge rate
        self.volts = int(self.args.get("volts", 240))                    # Assume L2 charging (adjust if needed)
        self.home_battery_min_soc = int(self.args.get("home_battery_min_soc", 90))  # Minimum home battery activation %
        self.buffer_watts = int(self.args.get("buffer_watts", 500))      # Safety buffer to avoid grid draw
        self.cooldown = int(self.args.get("cooldown", 15))               # Seconds to wait after each adjustment

        # State
        self.notify_handler = None
        self.eval_lock = False

        # Entities
        self.thermostat_state = "sensor.thermostat_state"
        self.home_soc_sensor = "sensor.solark_sol_ark_battery_soc"
        self.solar_sensor = "sensor.solark_sol_ark_solar_power"
        self.load_sensor = "sensor.solark_sol_ark_load_power"
        self.charge_rate = "input_number.tesla_charge_rate_master"
        self.charge_limit = "number.tesla_ble_charging_limit"
        self.target_soc_sensor = "input_number.tesla_solar_target_soc_limit"
        self.vehicle_soc_sensor = "sensor.tesla_battery_level"

        # Watch sensors
        self.listen_state(self.evaluate_charging, self.solar_sensor)
        self.listen_state(self.evaluate_charging, self.home_soc_sensor)
        self.listen_state(self.evaluate_charging, self.load_sensor)
        self.listen_state(self.evaluate_charging, self.target_soc_sensor)

        # Safe startup: disable charging until evaluated
        self.set_charge_rate(self.min_amps, disable=True)

        self.log("SolarEVCharger app initialized.")

    def evaluate_charging(self, entity, attribute, old, new, kwargs):
        try:
            home_soc = float(self.get_state(self.home_soc_sensor))
            vehicle_soc = int(float(self.get_state(self.vehicle_soc_sensor)))
            solar_watts = float(self.get_state(self.solar_sensor))
            load_watts = float(self.get_state(self.load_sensor))
            current_rate = float(self.get_state(self.charge_rate))
            target_soc = int(float(self.get_state(self.target_soc_sensor)))
        except (TypeError, ValueError) as e:
            self.log(f"Invalid sensor reading - skipping. {e}", level="WARNING")
            return

        # Only charge when home, battery full enough, and target_soc != current_vehicle_soc
        # To genericise this (to allow other vehicle charging), remove the last check
        if home_soc < self.home_battery_min_soc or vehicle_soc >= target_soc:
            #self.log(f"Home Battery SOC {home_soc:.1f}%, Vehicle SOC {vehicle_soc}%. Blocking charging.")
            self.set_charge_rate(self.min_amps, disable=True)
            return

        # Skip if we're in cooldown
        if self.eval_lock:
            return

        # Current EV draw
        ev_power = current_rate * self.volts

        # Calculate true excess solar with buffer
        available_watts = solar_watts - (load_watts - ev_power) - self.buffer_watts
        available_watts = max(0, available_watts)  # no negatives

        # Convert to amps and clamp
        target_amps = int(available_watts / self.volts)
        target_amps = max(self.min_amps, min(self.max_amps, target_amps))

        if target_amps > self.min_amps:
            self.set_charge_rate(target_amps)
        else:
            self.set_charge_rate(self.min_amps, disable=True)

    def _turn_on_notice(self, kwargs):
        self.turn_on("automation.tesla_charge_limit_change_notice")

    def _unlock_eval(self, kwargs):
        self.eval_lock = False
        # self.log("Cooldown expired - evaluations unlocked.")

    def set_charge_rate(self, amps, disable=False):
        target_soc = float(self.get_state(self.target_soc_sensor))

        # Cancel any delayed re-enables of notice, only if still valid
        if self.notify_handler:
            if self.info_timer(self.notify_handler):
                self.cancel_timer(self.notify_handler)
            self.notify_handler = None

        try:
            current_limit = float(self.get_state(self.charge_limit))
        except (TypeError, ValueError):
            current_limit = 0

        try:
            current_rate = float(self.get_state(self.charge_rate))
        except (TypeError, ValueError):
            current_rate = 0

        #self.log(f"{disable}")

        if disable:
            if current_limit != 50 or current_rate != self.min_amps:
                self.log(f"Disabling charging - limit=50%, rate={self.min_amps}A.")
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.charge_limit, value=50)
                self.set_value(self.charge_rate, self.min_amps)
                self.notify_handler = self.run_in(self._turn_on_notice, 30)
                # Start cooldown lock
                self.eval_lock = True
                self.run_in(self._unlock_eval, self.cooldown)
        else:
            if current_limit != target_soc or current_rate != amps:
                if current_rate != amps:
                    self.log(f"Updating charge rate to {amps}A (SOC limit {int(target_soc)}%).")
                    self.set_value(self.charge_rate, amps)

                if current_limit != target_soc:
                    self.turn_off("automation.tesla_charge_limit_change_notice")
                    self.call_service("number/set_value", entity_id=self.charge_limit, value=target_soc)
                    self.notify_handler = self.run_in(self._turn_on_notice, 30)

                # Start cooldown lock
                self.eval_lock = True
                self.run_in(self._unlock_eval, self.cooldown)
