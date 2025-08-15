import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import math
import time

class EvChargerSmartControl(hass.Hass):

    def initialize(self):
        self.ev_switch = self.args["ev_switch"]  # e.g. switch.emporia_charger
        self.solar_sensor = self.args["solar_sensor"]
        self.battery_sensor = self.args["battery_sensor"]
        self.grid_export_sensor = self.args["grid_export_sensor"]
        self.grid_state_sensor = self.args["grid_state_sensor"]
        self.override_entity = self.args.get("override_entity", "input_boolean.ev_charge_override")
        self.amps_override_entity = self.args.get("amps_override_entity", "input_number.ev_charge_amps_override")
        self.vehicle_battery_soc = self.args["vehicle_battery_soc"]
        self.ev_device_tracker = self.args["ev_device_tracker"]

        self.min_amps = int(self.args.get("min_amps", 6))
        self.max_amps = int(self.args.get("max_amps", 40))
        self.battery_threshold = float(self.args.get("battery_threshold", 85))
        self.debounce_minutes = int(self.args.get("debounce_minutes", 10))

        self.last_change = datetime.min
        self.last_amps = self.min_amps
        self.last_update_ts = 0  # time.time() format

        # Listen for changes
        self.listen_state(self.evaluate_conditions, self.ev_device_tracker)
        self.listen_state(self.evaluate_conditions, self.vehicle_battery_soc)
        self.listen_state(self.evaluate_conditions, self.solar_sensor)
        self.listen_state(self.evaluate_conditions, self.grid_export_sensor)
        self.listen_state(self.evaluate_conditions, self.grid_state_sensor)
        self.listen_state(self.evaluate_conditions, self.battery_sensor)
        self.listen_state(self.evaluate_conditions, self.override_entity)
        self.listen_state(self.evaluate_conditions, self.amps_override_entity)
        self.evaluate_conditions(None, None, None, None, None)

    def evaluate_conditions(self, entity, attribute, old, new, kwargs):
        now = datetime.now()

        # Disable/enable charging with grid availability
        if entity == self.grid_state_sensor:
            if new == "off":
                self.log("Grid offline - disabling EV charging")
                self._set_charger_state(False, now)
                return
            elif new == "on":
                self.log("Grid online - enabling EV charging")
                self._set_charger_state(True, now)

        # Only debounce solar changes, not override boolean or override rate
        if now - self.last_change < timedelta(minutes=self.debounce_minutes) and entity not in [self.amps_override_entity, self.override_entity]:
            self.log("Debounce active - skipping evaluation")
            return

        # Vehicle Battery SOC Override
        try:
            vehicle_soc = float(self.get_state(self.vehicle_battery_soc))
            if vehicle_soc < 30:
                amps = self.max_amps
                self.log(f"Vehicle SoC low < 30% ({vehicle_soc}%) - charging at max rate: {amps}A")
                self._set_charger_amps_and_state(amps, True, now)
                return
        except (TypeError, ValueError):
            self.log("Invalid vehicle battery SoC data, skipping evaluation")

        # Manual Override
        override = self.get_state(self.override_entity) == "on"
        amps_override_raw = self.get_state(self.amps_override_entity)
        try:
            amps_override = float(amps_override_raw)
        except (TypeError, ValueError):
            amps_override = 0

        if override:
            amps = int(amps_override)
            self.log(f"Manual override ON with amps override set: {amps}A")
            self._set_charger_amps_and_state(amps, True, now)
            return

        # General Logic
        try:
            solar = float(self.get_state(self.solar_sensor))
            grid_export = float(self.get_state(self.grid_export_sensor))
            home_battery_soc = float(self.get_state(self.battery_sensor))
        except (TypeError, ValueError):
            self.log(f"Invalid solar sensor data, skipping evaluation and making no changes - EV charger {self.get_state(self.ev_switch).upper()} {self.get_state(self.ev_switch, attribute='charging_rate')}A")
            return

        surplus = grid_export if grid_export > 0 else 0
        #volts = 240 # used to scale rate

        self.log(f"Solar: {solar}W, Grid Export: {grid_export}W, Battery SoC: {home_battery_soc}%, Surplus: {surplus}W")

        # Home battery above threshold
        if home_battery_soc >= self.battery_threshold:
            # if self.min_amps <= amps_override <= self.max_amps:
            #     amps = int(amps_override)
            #     self.log(f"Battery healthy with amps override: charging at {amps}A")
            # else:
            #     amps = int(surplus / volts)
            #     amps = max(self.min_amps, min(amps, self.max_amps))
            #     self.log(f"Battery healthy - scaling amps: {amps}A")

            amps = compute_charging_amps(
                measured_surplus=surplus,
                current_amps=self.last_amps,
                volts=240,
                surplus_floor=-300,
                scale_factor=180,
                bias_offset=0,
                rounding='ceil',
                max_amps=self.max_amps,
                min_amps=self.min_amps,
                min_change=1.0,
                last_update_time=self.last_update_ts,
                hold_duration=30
            )

            self.log(f"Home battery SOC healthy - scaling amps based on solar excess: {amps}A")
            self._set_charger_amps_and_state(amps, True, now)

        # Home battery below threshold
        elif home_battery_soc < self.battery_threshold: #and surplus <= 0:
            self.log("Home battery low - disabling EV charging")
            self._set_charger_state(False, now)
            return

        # # Home battery below threshold with some surplus
        # else:
        #     # if self.min_amps <= amps_override <= self.max_amps:
        #     #     amps = int(amps_override)
        #     #     self.log(f"Battery low with some surplus and amps override: charging at {amps}A")
        #     # else:
        #     #     amps = self.min_amps
        #     #     self.log(f"Battery low with some surplus - charging at minimum amps: {amps}A")
        #     amps = self.min_amps
        #     self.log(f"Battery low with some surplus - charging at minimum amps: {amps}A")
        #     self._set_charger_amps_and_state(amps, True, now)

    def compute_charging_amps(
        measured_surplus,
        current_amps,
        volts,
        surplus_floor=-300,
        scale_factor=180,
        bias_offset=0,
        rounding='ceil',
        max_amps=32,
        min_amps=6,
        min_change=1.0,
        last_update_time=None,
        hold_duration=30
    ):
        # Predict surplus as if charger wasn't pulling current
        predicted_surplus = measured_surplus + (current_amps * volts)

        # Cap at floor
        usable_surplus = max(predicted_surplus, surplus_floor)

        # Calculate raw amps
        raw_amps = usable_surplus / scale_factor + bias_offset

        # Apply rounding
        if rounding == 'ceil':
            new_amps = math.ceil(raw_amps)
        elif rounding == 'floor':
            new_amps = math.floor(raw_amps)
        else:
            new_amps = round(raw_amps)

        # Clamp to allowable range
        new_amps = max(min_amps, min(max_amps, new_amps))

        # Hysteresis logic to prevent flapping
        if abs(new_amps - current_amps) < min_change:
            return current_amps  # No significant change

        if last_update_time and (time.time() - last_update_time < hold_duration):
            if new_amps < current_amps:
                return current_amps  # Don't drop too soon

        return new_amps

    def _set_charger_amps_and_state(self, amps, charger_on, now):
        current_state = self.get_state(self.ev_switch)
        # We don't have a direct way to get current amps, so just always call service to set amps
        # Set charger amps via service call
        self.log(f"Setting EV charger amps to {amps}A")
        self.call_service(
            "emporia_vue/set_charger_current",
            entity_id=self.ev_switch,
            current=amps
        )

        if charger_on and current_state != "on":
            self.log("Turning ON EV charger")
            self.turn_on(self.ev_switch)

        elif not charger_on and current_state != "off":
            self.log("Turning OFF EV charger")
            self.turn_off(self.ev_switch)

        self.last_change = now
        self.last_amps = amps
        self.last_update_ts = time.time()

    def _set_charger_state(self, charger_on, now):
        current_state = self.get_state(self.ev_switch)
        if charger_on and current_state != "on":
            self.log("Turning ON EV charger")
            self.turn_on(self.ev_switch)
            self.last_change = now
        elif not charger_on and current_state != "off":
            self.log("Turning OFF EV charger")
            self.turn_off(self.ev_switch)
            self.last_change = now
