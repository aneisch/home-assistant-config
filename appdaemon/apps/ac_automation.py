import appdaemon.appapi as appapi
import datetime


class AutoAdjust(appapi.AppDaemon):
  def initialize(self):

    #Compile our times
    self.morning_adjust_weekday = datetime.datetime.strptime(self.args["morning_adjust_weekday"], '%H:%M:%S').time()
    self.night_adjust_weekday = datetime.datetime.strptime(self.args["night_adjust_weekday"], '%H:%M:%S').time()
    self.morning_adjust_weekend = datetime.datetime.strptime(self.args["morning_adjust_weekend"], '%H:%M:%S').time()
    self.night_adjust_weekend = datetime.datetime.strptime(self.args["night_adjust_weekend"], '%H:%M:%S').time()

    #Set our time callbacks
    self.run_daily(self.adjust_morning, self.morning_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
    self.run_daily(self.adjust_night, self.night_adjust_weekday, constrain_days="mon,tue,wed,thu,fri")
    self.run_daily(self.adjust_morning, self.morning_adjust_weekend, constrain_days="sat,sun")
    self.run_daily(self.adjust_night, self.night_adjust_weekend, constrain_days="sat,sun")

    #Set our tracker callbacks
    if "device_tracker" in self.args:
      for sensor in self.split_device_list(self.args["device_tracker"]):
        self.listen_state(self.presence_adjust, sensor)
    self.listen_state(self.presence_adjust, self.args["door_trigger"])


  #Do stuff!
  def presence_adjust(self, entity, attribute, old, new, kwargs):
    if (old == "not_home" and new == "home") or (old == "Closed" and new == "Open" and self.get_state(self.args["device_tracker"]) == "not_home"):
      if old == "Closed" and new == "Open":
        self.log("Door opened...")
        self.set_state(self.args["device_tracker"], state = "home")
      if self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, datetime.datetime.now().time()) == True:
        self.log("Someone is home during the day")
        self.adjust_morning(kwargs)
      else:
        self.log("Someone is home at night")
        self.adjust_night(kwargs)

    elif old == "home" and new == "not_home":
      self.log("House is unoccupied... adjusting accordingly")
      if float(self.get_state("sensor.dark_sky_temperature")) <= 50:
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["winter_unoccupied"])
      elif float(self.get_state("sensor.dark_sky_temperature")) > 50:
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["summer_unoccupied"])


  def adjust_morning(self, kwargs):
    if float(self.get_state("sensor.dark_sky_temperature")) <= 50 and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home": 
        self.log("Mode: Heat, Winter Day")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["winter_day"])
      else:
        self.log("Mode: Heat, Winter Unoccupied")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["winter_unoccupied"])

    elif float(self.get_state("sensor.dark_sky_temperature")) > 50 and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Cool, Summer Day")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["summer_day"])
      else:
        self.log("Mode: Cool, Summer Unoccupied")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["summer_unoccupied"])


  def adjust_night(self, kwargs):
    if float(self.get_state("sensor.dark_sky_temperature")) <= 50 and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Heat, Winter Night")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["winter_night"])
      else:
        self.log("Mode: Heat, Winter Unoccupied")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["winter_unoccupied"])

    elif float(self.get_state("sensor.dark_sky_temperature")) > 50 and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Cool, Summer Night")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["summer_night"])
      else:
        self.log("Mode: Cool, Summer Unoccupied")
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")
          self.call_service("climate/set_temperature", entity_id = tstat, temperature = self.args["summer_unoccupied"])


  def time_in_range(self, start, end, x):
    if start <= end:
      return start <= x <= end
    else:
      return start <= x or x <= end
