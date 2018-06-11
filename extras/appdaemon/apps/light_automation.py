import appdaemon.plugins.hass.hassapi as hass


#Turn on a scene at given time (specified in apps.yaml) 
class SceneTime(hass.Hass):
  def initialize(self):
    time_on = self.parse_time(self.args["time_on"])
    self.run_daily(self.on, time_on)

  def on(self, kwargs):
    if self.get_state(self.args["device_tracker"]) == "home" and self.get_state(self.args["dependent_light"]) == "on":
      self.log(self.args["scene"])
      self.turn_on(self.args["scene"])
    else:
      pass
