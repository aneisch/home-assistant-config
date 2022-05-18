inputEntity = data.get('entity_id')
inputStateObject = hass.states.get(inputEntity)
inputState = inputStateObject.state
inputAttributesObject = inputStateObject.attributes.copy()

'''
1. Service charge: $7.00 per month; plus 
2. Energy charge: $0.1079 per kWh for all kWh, except $0.1033 per 
kWh for all kWh in the billing months of November through April; 
plus 
3. Transmission Delivery Adjustment:  $0.0140 per kWh. 
• Wind Watts Wind Energy Rate:  This optional service is available to customers 
on a first come, first served basis subject to the available supply. 
1. 10% participation: $0.1084 per kWh for all kWh, except $0.1038 per 
kWh for all kWh in the billing months of November through April. 
2. 50% participation: $0.1104 per kWh for all kWh, except $0.1058 per 
kWh for all kWh in the billing months of November through April. 
'''

summer_cost = 0.1079 + 0.0140
winter_cost = 0.1033 + 0.0140

month = datetime.datetime.now().date().month

# Between May and October
if  month >= 5 and month <= 10:
    current_cost = summer_cost
else:
    current_cost = winter_cost


if inputEntity == 'sensor.electric_utilities_summary':
    # Add $7 monthly charge to summary total
    inputAttributesObject['cost'] = '{:.2f}'.format(7 + (float(inputState) * current_cost))

    # Set custom sensor for tracking
    service_data = {"entity_id": "sensor.electricity_cost_monthly", "state": inputAttributesObject['cost'], "attributes": {"friendly_name": "Utilities Cost", "unit_of_measurement": "$", "icon":"mdi:currency-usd"}}
    hass.services.call("setter", "set", service_data)

else:
    inputAttributesObject['cost'] = '{:.2f}'.format((float(inputState) * current_cost))

#hass.bus.fire("debug", {"wow": ""})

if inputEntity == 'sensor.electric_utilities_daily':
    inputAttributesObject['ReadDateHuman'] = datetime.datetime.fromtimestamp(int(str(inputAttributesObject['ReadDate'])[:-3]))

hass.states.set(inputEntity, inputState, inputAttributesObject)