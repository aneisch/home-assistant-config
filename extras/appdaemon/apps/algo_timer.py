import appdaemon.appapi as appapi, sqlite3
from datetime import datetime, timedelta

class SmartTimer(appapi.AppDaemon):
  def initialize(self):
    
    # Path to our DB as defined in apps.yaml
    db_location = self.args["db_location"]

    # Set up callback and listen for state change of desired switch
    self.listen_state(self.calculate_times, self.args["entity_id"], db_location=db_location)
    self.log("Initializing.. DB located at: %s" % db_location)


  # Calculate the average amount of time a switch is on
  def calculate_times(self, entity, attribute, old, new, kwargs):

    # Only execute if turned on
    if new == "on":

      #Calculate past lengths of time
      conn = sqlite3.connect("file:" +  kwargs["db_location"] + "?mode=ro", uri=True)
      c = conn.cursor()
      c.execute('SELECT state,last_changed FROM states where entity_id = "' + self.args["entity_id"] + '"')

      results = c.fetchall()
      conn.close()
      if self.args["debug"]:
        self.log("Entity changed.. reprocessing times")

      records = 0
      times = []

      # Iterate through entity changed times and create a list of times spent "on"
      for result in results:
        if self.args["debug"]:
          self.log(result)
        process = False
        if result[0] == "on":
          on = result[1]
        else:
          off = result[1]
          process = True
        if process == True:
          # Takes "off" timestamp and subtracts "on" timestamp to find timedelta
          length = datetime.strptime(off, '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(on, '%Y-%m-%d %H:%M:%S.%f')
          if self.args["debug"]:
            self.log("Found length: " + str(length))
          times.append(length)
          records += 1

      # Calculate average time spent "on"
      average = sum(times, timedelta(0)) / len(times)
      # Get total seconds from datetime hours, minutes, seconds
      average_seconds = int(timedelta.total_seconds(average))

      if self.args["debug"]:
        self.log("Calculation complete, determined average on time of " + str(average))

      # Schedule our turn_off action in X seconds in the future, the average time entity has spent is "on"
      self.log("Scheduling turn_off of %s in %s seconds." % (self.args["entity_id"],str(average_seconds)))
      self.run_in(self.average_exceeded, average_seconds)


  def average_exceeded(self, kwargs):
      self.log("Average time exceeded, turning off %s" % self.args["entity_id"])
      # Turn off specified entity
      self.turn_off(self.args["entity_id"]) 
