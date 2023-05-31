from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt

from .const import CONF_DEVICES


def orbit_time_to_local_time(timestamp: str):
    """Converts the Orbit API timestamp to local time."""
    if timestamp is not None:
        return dt.as_local(dt.parse_datetime(timestamp))
    return None


def filter_configured_devices(entry: ConfigEntry, all_devices):
    """Filter the device list to those that are enabled in options."""
    filtered_devices = [
        d for d in all_devices if str(d["id"]) in entry.options[CONF_DEVICES]
    ]

    # Ensure that all devices have a name
    for device in filtered_devices:
        if device.get("name") is None:
            device["name"] = "Unknown Device"

    return filtered_devices
