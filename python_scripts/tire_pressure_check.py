# Check tire pressure and alert if attetion is needed

inputs = ['sensor.tesla_tpms_pressure_fl', 'sensor.tesla_tpms_pressure_fr', 'sensor.tesla_tpms_pressure_rl', 'sensor.tesla_tpms_pressure_rr']
pressures = []
average_pressure_alert = 40
difference_alert = 2

for tire in inputs:
    pressures.append(float(hass.states.get(tire).state))

# Fire event containting max, min, and average pressure
# hass.bus.fire("warn", [max(pressures), min(pressures),sum(pressures) / len(pressures)])

# Alert if pressure difference between highest and lowest is > difference_alert
if max(pressures) - min(pressures) > difference_alert:
    hass.bus.fire("warn", [max(pressures), min(pressures), "too big"])
    hass.services.call("notify", "signal_homeassistant", {'message': f'''Tesla tire pressure needs attention. Min/Max difference >{difference_alert}psi.

Front Left: {hass.states.get('sensor.tesla_tpms_pressure_fl').state}
Front Right: {hass.states.get('sensor.tesla_tpms_pressure_fr').state}
Rear Left: {hass.states.get('sensor.tesla_tpms_pressure_rl').state}
Rear Right: {hass.states.get('sensor.tesla_tpms_pressure_rr').state}
'''})

# Alert if average pressure is below average_pressure_alert
if sum(pressures) / len(pressures) < average_pressure_alert:
    hass.services.call("notify", "signal_homeassistant", {'message': f'''Tesla tire pressure needs attention. Average pressure <{average_pressure_alert}psi

Average: {sum(pressures) / len(pressures)}
Front Left: {hass.states.get('sensor.tesla_tpms_pressure_fl').state}
Front Right: {hass.states.get('sensor.tesla_tpms_pressure_fr').state}
Rear Left: {hass.states.get('sensor.tesla_tpms_pressure_rl').state}
Rear Right: {hass.states.get('sensor.tesla_tpms_pressure_rr').state}
'''})