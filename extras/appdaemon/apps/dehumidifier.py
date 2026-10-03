import appdaemon.plugins.hass.hassapi as hass
import datetime

HUMIDIFIER = "humidifier.151732606535142_humidifier"

class SolarHumidifier(hass.Hass):
    def initialize(self):
        # Hysteresis: turn on above on_watts, only turn off once below off_watts
        self.on_watts = float(self.args.get("solar_on_watts", 1000))
        self.off_watts = float(self.args.get("solar_off_watts", 700))
        # Minimum seconds between solar-driven on/off changes (protects the compressor)
        self.min_cycle = int(self.args.get("min_cycle_seconds", 300))
        self.last_change = None

        # Watch solar power and occupancy
        self.listen_state(self.evaluate, "sensor.solark_sol_ark_solar_power")
        self.listen_state(self.evaluate, "group.trackers")

        # Run once at startup
        self.run_in(self.evaluate, 1)

    def evaluate(self, *args, **kwargs):
        try:
            solar = float(self.get_state("sensor.solark_sol_ark_solar_power") or 0)
        except (TypeError, ValueError):
            solar = 0

        occupied = self.get_state("group.trackers") == "home"
        is_on = self.get_state(HUMIDIFIER) == "on"

        if occupied:
            # Someone home → OFF immediately
            if self.get_state(HUMIDIFIER) != "off":
                self.set_humidifier(False, "someone home")
            return

        threshold = self.off_watts if is_on else self.on_watts
        want_on = solar >= threshold
        if want_on == is_on:
            return

        now = datetime.datetime.now()
        if self.last_change and (now - self.last_change).total_seconds() < self.min_cycle:
            return

        if want_on:
            self.set_humidifier(True, f"solar {solar:.0f}W >= {self.on_watts:.0f}W and nobody home")
        else:
            self.set_humidifier(False, f"solar {solar:.0f}W < {self.off_watts:.0f}W")

    def set_humidifier(self, on, reason):
        self.call_service("humidifier/turn_on" if on else "humidifier/turn_off", entity_id=HUMIDIFIER)
        self.last_change = datetime.datetime.now()
        self.log(f"Humidifier turned {'ON' if on else 'OFF'} ({reason})")
