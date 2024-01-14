import appdaemon.plugins.hass.hassapi as hass
import json
import time
from datetime import datetime

class TimerSync(hass.Hass):
    def initialize(self):

        self.alexa_timer = self.args["alexa_timer"]
        self.timer_prefix = self.args["timer_prefix"]
        self.timer_count = self.args["timer_count"]

        self.listen_state(self.state_change, self.alexa_timer, attribute = "sorted_active")

    def state_change(self, entity, attribute, old, new, kwargs):
        new = new.replace("null",'""')
        new = json.loads(new)
        count = 0

        self.log(new)
        self.log(count)

        for i in range(0,6):
            self.call_service("timer/cancel", entity_id = f"timer.{self.timer_prefix}_{i}")

        for timer in new:
            count += 1
            timer = timer[1]
            label = timer['timerLabel']
            if label == "":
                label = "No Name"
            trigger_time = int(timer['triggerTime']/1000)

            self.log(f"{label}: {trigger_time}")

            current_time = datetime.fromtimestamp(time.time())
            trigger_time = datetime.fromtimestamp(trigger_time)
            duration = str(trigger_time - current_time).split(".")[0]
            if "-" not in str(duration):
                self.log(f"now: {current_time} end: {trigger_time} length: {duration}")
                self.call_service("timer/start", entity_id = f"timer.{self.timer_prefix}_{count}", duration = f"{duration}")
                self.call_service("input_text/set_value", entity_id = f"input_text.{self.timer_prefix}_{count}_name", value = label)
            else:
                count -= 1