"""Provide info to system health."""
from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass):
    """Get info for the info page."""
    client = hass.data[DOMAIN]
    network_sensor = f"binary_sensor.{client['network_sensor']}"

    return {
        "zwave_integration": client["zwave_integration"],
        "network_status": hass.states.get(network_sensor).state,
    }
