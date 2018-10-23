import appdaemon.plugins.hass.hassapi as hass
import datetime


class AutoAdjust(hass.Hass):
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

  def set_heat(self, kwargs):
    for tstat in self.split_device_list(self.args["thermostats"]):
      self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "heat") 

  def set_cool(self, kwargs):
    for tstat in self.split_device_list(self.args["thermostats"]):
      self.call_service("climate/set_operation_mode", entity_id = tstat, operation_mode = "cool")

  def adjust_temp(self, kwargs):
    for tstat in self.split_device_list(self.args["thermostats"]):
      self.call_service("climate/set_temperature", entity_id = tstat, temperature = kwargs["temp"])


  #Set temperature based on whether house is occupied
  def presence_adjust(self, entity, attribute, old, new, kwargs):
    #Only change things if you AC automation switched to on
    if self.get_state(self.args["override_input_boolean"]) == "on":
      # If a tracker turns "home" OR the front door opens..
      if (old == "not_home" and new == "home") or (old == "off" and new == "on" and self.get_state(self.args["device_tracker"]) == "not_home"):
        if old == "off" and new == "on":
          self.log("Door open detected...")
          self.set_state(self.args["device_tracker"], state = "home")
        if self.time_in_range(self.morning_adjust_weekday, self.night_adjust_weekday, datetime.datetime.now().time()) == True:
          self.log("Someone is home during the day")
          self.adjust_morning(kwargs)
        else:
          self.log("Someone is home at night")
          self.adjust_night(kwargs)

      elif old == "home" and new == "not_home":
        if self.get_state("sensor.thermostat_operating_mode") == "Heat" and self.get_state("input_boolean.ac_automation") == "on":
          self.log("Mode: Heat, House is newly unoccupied, %s" % self.args["winter_unoccupied"])
          for tstat in self.split_device_list(self.args["thermostats"]):
            self.run_in(self.adjust_temp, 5, temp = self.args["winter_unoccupied"])
        elif self.get_state("sensor.thermostat_operating_mode") == "Cool" and self.get_state("input_boolean.ac_automation") == "on":
          self.log("Mode: Cool, House is newly unoccupied, %s" % self.args["summer_unoccupied"])
          for tstat in self.split_device_list(self.args["thermostats"]):
            self.run_in(self.adjust_temp, 5, temp = self.args["summer_unoccupied"])

  #Set daytime temperature (occupied/unoccupied)
  def adjust_morning(self, kwargs):
    if self.get_state("sensor.thermostat_operating_mode") == "Heat" and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home": 
        self.log("Mode: Heat, Winter Day, %s" % self.args["winter_day"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["winter_day"])
      else:
        self.log("Mode: Heat, Winter Unoccupied, %s" % self.args["winter_unoccupied"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["winter_unoccupied"])

    elif self.get_state("sensor.thermostat_operating_mode") == "Cool" and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Cool, Summer Day, %s" % self.args["summer_day"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["summer_day"])
      else:
        self.log("Mode: Cool, Summer Unoccupied, %s" % self.args["summer_unoccupied"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["summer_unoccupied"])

  #Set nighttime temperature (occupied/unoccupied)
  def adjust_night(self, kwargs):
    if self.get_state("sensor.thermostat_operating_mode") == "Heat" and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Heat, Winter Night, %s" % self.args["winter_night"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["winter_night"])
      else:
        self.log("Mode: Heat, Winter Unoccupied, %s" % self.args["winter_unoccupied"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["winter_unoccupied"])

    elif self.get_state("sensor.thermostat_operating_mode") == "Cool" and self.get_state("input_boolean.ac_automation") == "on":
      if self.get_state(self.args["device_tracker"]) == "home":
        self.log("Mode: Cool, Summer Night, %s" % self.args["summer_night"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["summer_night"])
      else:
        self.log("Mode: Cool, Summer Unoccupied, %s" % self.args["summer_unoccupied"])
        for tstat in self.split_device_list(self.args["thermostats"]):
          self.run_in(self.adjust_temp, 5, temp = self.args["summer_unoccupied"])

  #Determine whether we're in daytime or nighttime
  def time_in_range(self, start, end, x):
    if start <= end:
      return start <= x <= end
    else:
      return start <= x or x <= end
