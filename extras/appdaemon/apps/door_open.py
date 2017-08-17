import appdaemon.appapi as appapi


class DoorLight(appapi.AppDaemon):
  def initialize(self):
    if "door_sensor" in self.args:
      for sensor in self.split_device_list(self.args["door_sensor"]):
        self.listen_state(self.state_change, sensor)

  def state_change(self, entity, attribute, old, new, kwargs):
    for light in self.split_device_list(self.args["lights"]):
      if new == "Open" and self.get_state(light) == "off":
        self.log("Turning " + light + " On")
        self.turn_on(light)
        self.run_in(self.light_off, self.args["time_on"], switch=light)
      elif new == "Open" and self.get_state(light) == "on":
        pass

  def light_off(self, args):
    self.log("Turning " + args["switch"] + " Off")
    self.turn_off(args["switch"])


class DoorNotify(appapi.AppDaemon):
  def initialize(self):
    if "door_sensor" in self.args:
      for sensor in self.split_device_list(self.args["door_sensor"]):
        self.listen_state(self.state_change, sensor)

  def state_change(self, entity, attribute, old, new, kwargs):
    if entity == "sensor.front_door_status" and new == "Open" and self.get_state("input_boolean.door_notify") == "on":
      self.log(entity + "changed to opened, notifying")
      self.call_service("notify/" + self.args["notify"], title = "Home Assistant", message = "Front Door Opened")
    elif entity == "sensor.back_door_status" and new == "Open" and self.get_state("input_boolean.door_notify") == "on":
      self.log(entity + "changed to opened, notifying")
      self.call_service("notify/" + self.args["notify"], title = "Home Assistant", message = "Back Door Opened")
