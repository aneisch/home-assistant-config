MeterEntity = data.get('meter_entity')
inputStateObject = hass.states.get(MeterEntity)
inputState = inputStateObject.state
inputAttributesObject = inputStateObject.attributes.copy()

usage = inputState
usage = 5000

# 0 < usage < 10,000 = 2.40/1000gal
# 11,000 < usage < 15,000 = 3.12/1000gal
# 16,000 < usage < 20,000 = 3.83/1000gal
computed_cost = 0

if usage <= 11000:
    computed_cost =  (usage / 1000) * 2.40

debug = computed_cost

# Add $10.80 monthly meter charge to summary total
inputAttributesObject['cost'] = '{:.2f}'.format(10.80 + computed_cost)

hass.bus.fire("debug", {"debug": debug, "result": '{:.2f}'.format(10.80 + computed_cost)})

# hass.states.set(MeterEntity, inputState, inputAttributesObject)
# service_data = {"entity_id": "input_text.water_cost_monthly", "value": inputAttributesObject['cost']}
# hass.services.call("input_text", "set_value", service_data)