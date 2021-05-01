inputEntity = data.get('entity_id')
inputStateObject = hass.states.get(inputEntity)
inputState = inputStateObject.state
inputAttributesObject = inputStateObject.attributes.copy()
inputAttributesObject['cost'] = '{:.2f}'.format(float(inputState)*0.11)
if inputEntity == 'sensor.electric_utilities_daily':
    inputAttributesObject['ReadDateHuman'] = datetime.datetime.fromtimestamp(int(str(inputAttributesObject['ReadDate'])[:-3]))
hass.states.set(inputEntity, inputState, inputAttributesObject)


