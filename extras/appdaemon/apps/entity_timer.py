import appdaemon.plugins.hass.hassapi as hass
import time

class Timer(hass.Hass):
  def initialize(self):
    if "time_on" in self.args:
      time_on = self.parse_time(self.args["time_on"])
      self.run_daily(self.on, time_on)

    if "time_off" in self.args:
      time_off = self.parse_time(self.args["time_off"])
      self.run_daily(self.off, time_off)

  def on(self, kwargs):
    for device in self.split_device_list(self.args["entities"]):
        self.log("Turning on " + device)
        if "brightness" in self.args and "light." in device: # API failure if we pass brightness when non-light
          self.turn_on(device, brightness = self.args["brightness"])
        else:
          self.turn_on(device)
          time.sleep(0.5)

  def off(self, kwargs):
    for device in self.split_device_list(self.args["entities"]):
        self.log("Turning off " + device)
        self.turn_off(device)
