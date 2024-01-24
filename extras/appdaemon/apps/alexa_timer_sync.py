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

        for i in range(0,6):
            self.call_service("timer/cancel", entity_id = f"timer.{self.timer_prefix}_{i}")

        for timer in new:
            count += 1
            timer = timer[1]
            label = timer['timerLabel']
            if label == "":
                label = "No Name"
            trigger_time = int(timer['triggerTime']/1000)
            created_time = int(timer['createdDate']/1000)
            timer_id = timer['id'][-8:] # Just grab the last 8 digits of the ID

            # Calculate original length in h:m:s
            millis = int(timer['originalDurationInMillis'])
            seconds=int(millis/1000)%60
            minutes=int(millis/(1000*60))%60
            hours=int(millis/(1000*60*60))%24
            pretty_length =  f"{hours}h {minutes}m {seconds}s"
            current_time = datetime.fromtimestamp(time.time())
            trigger_time = datetime.fromtimestamp(trigger_time)
            created_time = datetime.fromtimestamp(created_time)
            duration = str(trigger_time - current_time).split(".")[0]

            if "-" not in str(duration):
                self.log(f"{label} - ID: {timer_id} - Created: {created_time} - Start: {current_time} - End: {trigger_time} - Original Length: {pretty_length} - Calculated Remaining: {duration}")
                self.call_service("timer/start", entity_id = f"timer.{self.timer_prefix}_{count}", duration = f"{duration}")
                self.call_service("input_text/set_value", entity_id = f"input_text.{self.timer_prefix}_{count}_name", value = label)
            else:
                count -= 1