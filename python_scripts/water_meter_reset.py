ResetEntity = data.get('cycle_reset_entity_id')
MeterEntity = data.get('meter_entity')

# Handle Meter Reset -- Run daily at midnight via automation
inputStateObject = hass.states.get(ResetEntity)
inputAttributesObject = inputStateObject.attributes.copy()
now = datetime.datetime.now()
start = datetime.datetime.strptime(inputAttributesObject['StartDate'], "%a %b %d, %Y")
#start = datetime.datetime.strptime('Tue Aug 19, 2023', "%a %b %d, %Y") # test

# Ensure we only reset at midnight on the start date
if start.day == now.day and now.hour == 0:
    hass.bus.fire("warn", {'StartDate': start, 'Now': now, 'Action': "Reset", "ah": MeterEntity})
    hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})

else:
    hass.bus.fire("warn", {'StartDate': start, 'Now': now, 'Action': "None"})