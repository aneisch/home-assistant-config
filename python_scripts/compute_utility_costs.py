MeterEntity = data.get('meter_entity')
inputState = hass.states.get(MeterEntity).state

'''
Electric:
1. Service charge: $7.00 per month; plus
2. Energy charge: $0.1187 per kWh for all kWh; plus
3. Transmission Delivery Adjustment: $0.0175 per kWh.
'''
current_cost = 0.1187 + 0.0175

if MeterEntity == "sensor.electricity_usage":
    #hass.bus.fire("debug", {"wow": ""})

    # Add $7 monthly charge to summary total
    computed_electricity_cost = round(7 + ((float(inputState)) * current_cost), 2)

    # Set State
    service_data = {"entity_id": "input_text.electricity_cost_monthly_emporia", "value": computed_electricity_cost}
    hass.services.call("input_text", "set_value", service_data)

elif MeterEntity == "sensor.tesla_energy_this_month":
    # Add $7 monthly charge to summary total
    computed_electricity_cost = round((float(inputState) * current_cost), 2)

    # Set State
    service_data = {"entity_id": "input_text.electricity_cost_monthly_tesla", "value": computed_electricity_cost}
    hass.services.call("input_text", "set_value", service_data)

elif MeterEntity == "sensor.water_usage":
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