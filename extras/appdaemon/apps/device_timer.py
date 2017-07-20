import appdaemon.appapi as appapi


class Timer(appapi.AppDaemon):
  def initialize(self):
    time_on = self.parse_time(self.args["time_on"])
    time_off = self.parse_time(self.args["time_off"])
    self.run_daily(self.on, time_on)
    self.run_daily(self.off, time_off)

  def on(self, kwargs):
    for device in self.split_device_list(self.args["devices"]):
        self.log("Turning on " + device)
        self.turn_on(device)

  def off(self, kwargs):
    for device in self.split_device_list(self.args["devices"]):
        self.log("Turning off " + device)
        self.turn_on(device)
