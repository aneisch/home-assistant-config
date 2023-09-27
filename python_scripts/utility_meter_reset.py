ResetEntity = data.get('cycle_reset_entity_id')
MeterEntity = data.get('meter_entity')

# Handle Meter Reset -- Run daily at midnight via automation

# Get state of reset entity (probably sensor.utilities_cycle_start)
cycleStateObject = hass.states.get(ResetEntity).state
# Get current datetime
now = datetime.datetime.now()

# Convert reset entity state to datetime object
start = datetime.datetime.strptime(cycleStateObject, "%Y-%m-%d")

# Ensure we only reset at midnight on the start date
if start.day == now.day and start.month == now.month and now.hour == 0:
    hass.bus.fire("warn", {'StartDate': start, 'Now': now, 'Action': "Reset", "Meter": MeterEntity})
    hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})

else:
    hass.bus.fire("warn", {'StartDate': start, 'Now': now, 'Action': "None", "Meter": MeterEntity})