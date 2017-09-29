import appdaemon.appapi as appapi

"""
Notifies the specified notifier on
the days you specify.
"""

class Notify(appapi.AppDaemon):
  def initialize(self):
    if "countdown_entity" in self.args:
      self.listen_state(self.evaluate_notice, self.args["countdown_entity"])

  def evaluate_notice(self, entity, attribute, old, new, kwargs):
    days_remaining = self.get_state(entity, "days_remaining")
    entity_friendly_name = self.get_state(entity, "friendly_name")

    if type(self.args["notification_days"]) == int:
      notification_days = [self.args["notification_days"]]
    else:
      notification_days = [int(day) for day in self.args["notification_days"].split(",")]

    if days_remaining in notification_days:
      self.send_notice()
    elif self.args["notify_overdue"] and days_remaining < 0:
      self.send_notice()      

  def send_notice(self):
    self.log("Sending notification")
    self.call_service("notify/" + self.args["notify"], message = self.args["message"])
    self.call_service("persistent_notification/create", message = self.args["message"])
