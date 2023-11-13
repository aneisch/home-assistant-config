MeterEntity = data.get('meter_entity')
inputState = hass.states.get(MeterEntity).state

unaccountedusage = int(float(inputState))
computed_water_cost = 12.40 # meter charge
computed_sewer_cost = 22.55 # base sewer up 4k gallons water usage

# Sewer based on water consumption
tier2sewer = 4.50

if unaccountedusage >= 10000:
    computed_sewer_cost = 49.70
elif unaccountedusage <= 4000:
    pass
else:
    tier2sewerusage = min(6000, unaccountedusage - 4000)
    computed_sewer_cost = computed_sewer_cost + (tier2sewerusage / 1000) * tier2sewer

# Water consumption
tier1rate = 2.75
tier2rate = 3.60
tier3rate = 4.40
tier4rate = 5.20
tier5rate = 6.05

tier1usage = min(10000, unaccountedusage)
unaccountedusage = unaccountedusage - tier1usage

tier2usage = min(5000, unaccountedusage)
unaccountedusage = unaccountedusage - tier2usage

tier3usage = min(5000, unaccountedusage)
unaccountedusage = unaccountedusage - tier3usage

tier4usage = min(5000, unaccountedusage)
unaccountedusage = unaccountedusage - tier4usage

tier5usage = unaccountedusage

computed_water_cost = computed_water_cost \
    + (tier1usage / 1000) * tier1rate \
    + (tier2usage / 1000) * tier2rate \
    + (tier3usage / 1000) * tier3rate \
    + (tier4usage / 1000) * tier4rate \
    + (tier5usage / 1000) * tier5rate


# Add water and sewer
computed_water_cost = round(computed_water_cost, 2)
computed_sewer_cost = round(computed_sewer_cost, 2)

# Set states
service_data = {"entity_id": "input_text.water_cost_monthly", "value": computed_water_cost}
hass.services.call("input_text", "set_value", service_data)

service_data = {"entity_id": "input_text.sewer_cost_monthly", "value": computed_sewer_cost}
hass.services.call("input_text", "set_value", service_data)