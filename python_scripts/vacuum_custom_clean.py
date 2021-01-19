"""
Take input from a number of input_select and then tell Roborock to clean those rooms

miiocli vacuum --ip 10.0.0.10 --token XX get_room_mapping

[[25, '825001006187'], [16, '825001003979'], [17, '825001006189'], [18, '825001003977'], [19, '825001003981'], [20, '825001003983'], [21, '825001003991'], [22, '825001004001'], [23, '825001003953'], [24, '825001003999'], [26, '825001004003'], [27, '825001004039']]
"""

rooms = {'Dining Room':22,'Kitchen':24,'Living Room':23,'Office':21,'Guest Bedroom':26,'Guest Bathroom':19,'Hallway':16,"Bethany's Office":20,'Master Bedroom':18,'Master Bathroom':27, 'Back Bathroom':17, 'Back Bedroom':25}

segments = []

# Iterate through input_selects and find rooms to clean
for i in range(1,11):
    state = hass.states.get("input_select.vacuum_custom_clean_" + str(i)).state
    if str(state) != "None":
      segments.append(rooms[state])

# Only call the service if at least one room is selected
if len(segments) > 0:
  service_data = {"entity_id": "vacuum.roborock_s4", "segments": segments}
  hass.services.call("xiaomi_miio", "vacuum_clean_segment", service_data, False)
