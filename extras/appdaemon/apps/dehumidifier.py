import appdaemon.plugins.hass.hassapi as hass

class SolarHumidifier(hass.Hass):
    def initialize(self):
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

        # Turn on if lots of solar or if switching to unoccupied (and solar)
        if solar >= 1000 or (not occupied and solar >= 1000):
            # Conditions met → turn ON
            if self.get_state("humidifier.151732606535142_humidifier") != "on":
                self.call_service("humidifier/turn_on",
                    entity_id="humidifier.151732606535142_humidifier")
                # self.call_service("climate/set_fan_mode",
                #     entity_id="climate.thermostat", fan_mode="med")
                self.log("Humidifier turned ON (solar >= 500W and nobody home)")
        else:
            # Otherwise → turn OFF
            if self.get_state("humidifier.151732606535142_humidifier") != "off":
                self.call_service("humidifier/turn_off",
                    entity_id="humidifier.151732606535142_humidifier")
                # self.call_service("climate/set_fan_mode",
                #     entity_id="climate.thermostat", fan_mode="auto")
                self.log("Humidifier turned OFF (insufficient solar or someone home)")