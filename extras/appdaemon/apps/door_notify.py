import appdaemon.appapi as appapi


class FrontDoorNotify(appapi.AppDaemon):

  def initialize(self):
    if "door_sensor" in self.args:
      for sensor in self.split_device_list(self.args["door_sensor"]):
        self.listen_state(self.state_change, sensor)

  def state_change(self, entity, attribute, old, new, kwargs):
    if entity == "sensor.front_door_status" and new == "Open" and self.get_state("input_boolean.door_notify") == "on":
      self.call_service("notify/notify_push_android", title = "Home Assistant", message = "Front Door Opened")
    elif entity == "sensor.back_door_status" and new == "Open" and self.get_state("input_boolean.door_notify") == "on":
      self.call_service("notify/notify_push_android", title = "Home Assistant", message = "Back Door Opened")
