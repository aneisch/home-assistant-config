ResetEntity = data.get('cycle_reset_entity_id')
MeterEntity = data.get('meter_entity')

###
# Comment this out once the sensor.utilities_cycle_end is fixed
# This manual workaround ensures that the meter is reset on the 1st of the month
# now = datetime.datetime.now()
# if now.day == 1:
#     hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})
# Rest is ignored, see above 
###

# Handle Meter Reset -- Run daily at midnight via automation

# Get state of reset entity and get dt
cycleStateObject = hass.states.get(ResetEntity).state
end_dt = datetime.datetime.strptime(cycleStateObject, "%Y-%m-%d")
end_date = end_dt.date()

# Calculate the day after the cycle ends
# No lets do day of
reset_day = end_date # + datetime.timedelta(days=1)

# Get today's date
today = datetime.datetime.now().date()

# Ensure we only reset at midnight on the end date
if today == reset_day:

    # Send bill estimate
    # Hacky way to ensure estimate only gets sent once
    if MeterEntity == "sensor.electricity_usage":
        cycle_end = hass.states.get('sensor.utilities_cycle_end').state
        water_cost = float(hass.states.get('input_text.water_cost_monthly').state)
        sewer_cost = float(hass.states.get('input_text.sewer_cost_monthly').state)
        electric_cost = float(hass.states.get('input_text.electricity_cost_monthly').state) + 7 # Add monthly service charge
        electric_credit = float(hass.states.get('input_text.electricity_sell_monthly').state) *-1
        # Trash, drainage fee, roadway fee
        other_cost = 22.25 + 7.50 + 10.25
        total = water_cost + sewer_cost + electric_cost + electric_credit + other_cost
        message = f"""
Utilities Estimate for Cycle ending {cycle_end}:
Water: ${water_cost:.2f}
Sewer: ${sewer_cost:.2f}
Electric Usage: ${electric_cost:.2f}
Electric Production: ${electric_credit:.2f}
Other: ${other_cost:.2f}
Total: ${total:.2f}
"""
        hass.services.call("notify", "signal_homeassistant", {"message": f"{message}"})

    hass.services.call("utility_meter", "calibrate", {'value': '0', 'entity_id': MeterEntity})
    hass.services.call("notify", "signal_homeassistant", {"message": f"{MeterEntity} has been reset for the cycle!"})
# else:
#     hass.services.call("notify", "signal_homeassistant", {"message": f"{MeterEntity} will be reset for the cycle on {reset_day}. It is {today}!"})
