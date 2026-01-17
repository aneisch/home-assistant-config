import appdaemon.plugins.hass.hassapi as hass
import json
from datetime import datetime, timedelta
import time

class TimerSync(hass.Hass):
    def initialize(self):
        self.timer_count = int(self.args.get("timer_count", 1))
        self.alexa_timer = self.args["alexa_timer"]
        self.timer_prefix = self.args["timer_prefix"]

        self.listen_state(self.state_change, self.alexa_timer, attribute="sorted_active")

    def state_change(self, entity, attribute, old, new, kwargs):
        # try:
        #     self.log(new)
        #     #new = new.replace("null", '""')  # Safeguard for nulls
        #     timers = new
        # except Exception as e:
        #     self.error(f"Failed to parse timers from Alexa: {e}")
        #     return

        # Cancel all existing timers
        for i in range(self.timer_count + 1):
            self.call_service("timer/cancel", entity_id=f"timer.{self.timer_prefix}_{i}")

        count = 0
        for timer_entry in new:
            if count >= self.timer_count:
                break
            self.log(timer_entry)
            timer = timer_entry
            label = timer.get("timerLabel") or "No Name"
            self.log(label)
            trigger_time = datetime.fromtimestamp(int(timer["triggerTime"] / 1000))
            created_time = datetime.fromtimestamp(int(timer["createdDate"] / 1000))
            timer_id = timer["id"][-8:]

            # Duration calculation
            millis = int(timer.get("originalDurationInMillis", 0))
            pretty_length = str(timedelta(milliseconds=millis))

            now = datetime.now() - timedelta(seconds=3)  # Account for slight lag
            remaining = trigger_time - now
            if remaining.total_seconds() <= 0:
                continue  # Skip expired/invalid timers

            duration = str(remaining).split(".")[0]  # Drop microseconds
            self.log(
                f"[{label}] - ID: {timer_id} - Created: {created_time} - "
                f"Now: {now} - End: {trigger_time} - Original: {pretty_length} - Remaining: {duration}"
            )

            count += 1
            self.call_service(
                "timer/start",
                entity_id=f"timer.{self.timer_prefix}_{count}",
                duration=duration
            )
            self.call_service(
                "input_text/set_value",
                entity_id=f"input_text.{self.timer_prefix}_{count}_name",
                value=label
            )
