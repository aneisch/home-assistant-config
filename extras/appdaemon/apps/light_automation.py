import appdaemon.plugins.hass.hassapi as hass

#Turn on a scene at given time (specified in apps.yaml)
class DeviceOn(hass.Hass):
    def initialize(self):
      time_on = self.parse_time(self.args["time_on"])
      self.run_daily(self.on, time_on)

    def on(self, kwargs):
        for entity in self.split_device_list(self.args["entity"]):
            self.log("Turning on" + entity)
            self.turn_on(entity)
