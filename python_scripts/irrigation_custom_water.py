"""
Take input from a number of input_select and then tell Node Red what to water
"""

zones = {"zones":[]}

# Iterate through input_selects and find zones to water
for i in range(1,6):
    state = hass.states.get("input_select.irrigation_custom_water_" + str(i)).state

    if str(state) != "None":
      zone_entity_id = "switch.irrigation_" + state.lower().replace(" ","_")

      # Default front beds to 5 minutes
      if "Front Beds" in state:
       time = 5
      else:
        time = 10

      entry = {"zone": zone_entity_id, "time": time}


      zones["zones"].append(entry)

# Only call the service if at least one zone is selected
if len(zones) > 0:
  hass.bus.fire("irrigation_custom_water", zones)