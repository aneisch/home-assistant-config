import appdaemon.plugins.hass.hassapi as hass

#
# App to respond to buttons on an Aeotec Minimote
#
# Args:
#
# Minimote can send up to 8 scenes. Odd numbered scenes are short presses of the buttons, even are long presses
#
# Args:
#
#device - name of the device. This will be the ZWave name without an entity type, e.g. minimote_31
#scene_<id>_on - name of the entity to turn on when scene <id> is activated
#scene_<id>_off - name of the entity to turn off when scene <id> is activated. If the entity is a scene it will be turned on.
#scene_<id>_toggle - name of the entity to toggle when scene <id> is activated
#
# Each scene can have up to one of each type of action, or no actions - e.g. you can turn on one light and turn off another light for a particular scene if desired
#
# Release Notes
#
# Version 1.0:
#   Initial Version

class ZigbeeRemote(hass.Hass):

  def initialize(self):
    
    self.listen_event(self.zha_event, "zha_event", device_ieee = self.args["device_ieee"])
    
  def zha_event(self, event_name, data, kwargs):
    self.log("Event: {}, data = {}, args = {}".format(event_name, data, kwargs))
    command = data["command"]
    buttons = { 'on': '1', 'off': '1', 'move_to_level': '2', 'move': '2_hold', 'move_to_color_temp': '3' }
    on = "button_{}_on".format(buttons[command])
    off = "button_{}_off".format(buttons[command])
    toggle = "button_{}_toggle".format(buttons[command])

    if on in self.args:
      self.log("Turning {} on".format(self.args[on]))
      self.turn_on(self.args[on])

    elif off in self.args:
      type, id = self.args[off].split(".")
      if type == "scene":
        self.log("Turning {} on".format(self.args[off]))
        self.turn_on(self.args[off])
      else:
        self.log("Turning {} off".format(self.args[off]))
        self.turn_off(self.args[off])

    elif toggle in self.args:
      self.log("Toggling {}".format(self.args[toggle]))
      self.toggle(self.args[toggle])
