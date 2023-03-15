"""Diagnostics support for BHyve."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLIENT, DOMAIN
from .pybhyve.client import Client

CONF_ALTITUDE = "altitude"
CONF_UUID = "uuid"

TO_REDACT = {
    "address",
    "full_location",
    "location",
    "weather_forecast_location_id",
    "weather_station_id",
    "image_url",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    bhyve: Client = hass.data[DOMAIN][entry.entry_id][CONF_CLIENT]

    devices = await bhyve.devices
    programs = await bhyve.timer_programs

    return async_redact_data({"devices": devices, "programs": programs}, TO_REDACT)
