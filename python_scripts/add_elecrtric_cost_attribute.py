MeterEntity = data.get('meter_entity')
inputState = hass.states.get(MeterEntity).state

'''
1. Service charge: $7.00 per month; plus
2. Energy charge: $0.1187 per kWh for all kWh; plus
3. Transmission Delivery Adjustment: $0.0175 per kWh.
'''

current_cost = 0.1187 + 0.0175

#hass.bus.fire("debug", {"wow": ""})

# Add $7 monthly charge to summary total
computed_electricity_cost = round(7 + ((float(inputState)) * current_cost), 2)

# Set State
service_data = {"entity_id": "input_text.electricity_cost_monthly_emporia", "value": computed_electricity_cost}
hass.services.call("input_text", "set_value", service_data)