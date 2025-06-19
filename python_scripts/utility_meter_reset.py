ResetEntity = data.get('cycle_reset_entity_id')
MeterEntity = data.get('meter_entity')

# Comment this out once the sensor.utilities_cycle_end is fixed
# This manual workaround ensures that the meter is reset on the 1st of the month
now = datetime.datetime.now()
if now.day == 1:
    hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})

###
# Rest is ignored, see above 
###


# Handle Meter Reset -- Run daily at midnight via automation

# Get state of reset entity (probably sensor.utilities_cycle_start)
cycleStateObject = hass.states.get(ResetEntity).state
# Get current datetime
now = datetime.datetime.now()

# Convert reset entity state to datetime object
end = datetime.datetime.strptime(cycleStateObject, "%Y-%m-%d")

# Ensure we only reset at midnight on the start date
if end.day == now.day and end.month == now.month and now.hour == 00:
    hass.bus.fire("warn", {'EndDate': end, 'Now': now, 'Action': "Reset", "Meter": MeterEntity})
    hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})

else:
    hass.bus.fire("warn", {'EndDate': end, 'Now': now, 'Action': "None", "Meter": MeterEntity})