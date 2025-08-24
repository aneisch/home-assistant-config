import appdaemon.plugins.hass.hassapi as hass

class SolarEVCharger(hass.Hass):

    def initialize(self):
        # Configurable constants
        self.min_amps = 6               # Emporia/Tesla minimum charge rate
        self.max_amps = 40              # Emporia/Tesla max charge rate
        self.buffer_watts = 1000        # Basic buffer watts setting
        self.volts = 240                # Assume L2 charging (adjust if needed)
        self.home_battery_min_soc = 90  # Minimum home battery activation %
        self.notify_handler = None      # Allows us to turn off "charge limit change notice" alerts
        self.low_buffer = 1500          
        self.mid_buffer = 2000
        self.high_buffer = 5000

        # Entities
        self.thermostat_state = "sensor.thermostat_state"
        self.soc_sensor = "sensor.solark_sol_ark_battery_soc"
        self.solar_sensor = "sensor.solark_sol_ark_solar_power"
        self.charge_rate = "input_number.tesla_charge_rate_master"
        self.charge_limit = "number.tesla_ble_charging_limit"
        self.target_soc_sensor = "input_number.tesla_solar_target_soc_limit"

        # Watch sensors
        self.listen_state(self.evaluate_charging, self.solar_sensor)
        self.listen_state(self.evaluate_charging, self.soc_sensor)

        self.log("SolarEVCharger app initialized.")

    def evaluate_charging(self, entity, attribute, old, new, kwargs):
        try:
            soc = float(self.get_state(self.soc_sensor))
            solar_watts = float(self.get_state(self.solar_sensor))
        except (TypeError, ValueError):
            self.log("Invalid sensor reading — skipping.")
            return

        thermostat_state = self.get_state(self.thermostat_state)
        # High Buffer
        if thermostat_state == "Cooling":
            if self.buffer_watts != self.high_buffer:
                self.log(f"A/C currently '{thermostat_state}'. Setting {self.high_buffer} buffer.")
                self.buffer_watts = self.high_buffer
        # Mid Buffer    
        elif thermostat_state == "Idle Fan":
            if self.buffer_watts != self.mid_buffer:
                self.log(f"A/C currently '{thermostat_state}'. Setting {self.mid_buffer} buffer.")
                self.buffer_watts = self.mid_buffer
        # Low Buffer
        else:
            if self.buffer_watts != self.low_buffer:
                self.log(f"A/C currently '{thermostat_state}'. Setting {self.low_buffer} buffer.")
                self.buffer_watts = self.low_buffer
                self.set_charge_rate(self.min_amps, disable=True)

        # Only charge when battery full
        if soc < self.home_battery_min_soc:
            #self.log(f"Battery SOC below {self.home_battery_min_soc}% ({soc}%). Blocking charging.")
            self.set_charge_rate(self.min_amps, disable=True)
            return

        # Calculate available solar power
        available_watts = max(0, solar_watts - self.buffer_watts)
        amps = int(available_watts / self.volts)

        # Clamp within safe range
        amps = max(self.min_amps, min(self.max_amps, amps))

        if amps > self.min_amps:
            #self.log(f"SOC={soc}%, solar={solar_watts}W. Charge rate: {amps}A")
            self.set_charge_rate(amps)
        else:
            #self.log(f"Not enough solar ({solar_watts}W) after buffer ({self.buffer_watts}W). Blocking charging.")
            self.set_charge_rate(self.min_amps, disable=True)

    def _turn_on_notice(self, kwargs):
        self.turn_on("automation.tesla_charge_limit_change_notice")

    def set_charge_rate(self, amps, disable=False):
        target_soc = float(self.get_state(self.target_soc_sensor))

        if self.notify_handler:
            self.cancel_timer(self.notify_handler)
            self.notify_handler = None

        if disable:
            # Disable charging only if not already disabled
            current_limit = self.get_state(self.charge_limit)
            try:
                current_limit = float(self.get_state(self.charge_limit))
            except:
                current_limit = 0 
            current_rate = float(self.get_state(self.charge_rate))

            if current_limit != 50 or current_rate != self.min_amps:
                self.log(f"Disabling charging (limit=50, rate={self.min_amps}).")
                # Disable charge limit notice
                self.turn_off("automation.tesla_charge_limit_change_notice")
                self.call_service("number/set_value", entity_id=self.charge_limit, value=50)
                self.set_value(self.charge_rate, self.min_amps)
                self.notify_handler = self.run_in(self._turn_on_notice, 30)
                #self.turn_on("automation.tesla_charge_limit_change_notice")

            # else:
            #     self.log("Charging already disabled. No change.")
        else:
            # Enable charging at amps, but only if different
            current_limit = self.get_state(self.charge_limit)
            try:
                current_limit = float(self.get_state(self.charge_limit))
            except:
                current_limit = 0 
            current_rate = float(self.get_state(self.charge_rate))

            if current_limit != target_soc or current_rate != amps:
                self.log(f"Updating charge rate to {amps}A.")
                self.set_value(self.charge_rate, amps)
                # Disable charge limit notice
                if current_limit != target_soc:
                    self.log(f"Updating SOC limit to {int(target_soc)}%.")
                    self.turn_off("automation.tesla_charge_limit_change_notice")
                    self.call_service("number/set_value", entity_id=self.charge_limit, value=target_soc)
                    self.notify_handler = self.run_in(self._turn_on_notice, 30)
            # else:
            #     self.log(f"Charge rate already {amps}A and BLE limit={target_soc}. No change.")