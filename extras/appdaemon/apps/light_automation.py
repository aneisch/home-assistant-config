import appdaemon.plugins.hass.hassapi as hass


#Turn on a scene at given time (specified in apps.yaml)
class DeviceOn(hass.Hass):
    def initialize(self):
      time_on = self.parse_time(self.args["time_on"])
      self.run_daily(self.on, time_on)

    def on(self, kwargs):
        if self.args["dependent_entity"]:
            if self.get_state(self.args["dependent_entity"]) == "on":
                for entity in self.split_device_list(self.args["entity"]):
                    self.log("Turning " + entity + " on")
                    self.turn_on(entity)
        else:
            if self.get_state(self.args["device_tracker"]) == "home":
                for entity in self.split_device_list(self.args["entity"]):
                    self.log("Turning " + entity + " on")
                    self.turn_on(entity)
