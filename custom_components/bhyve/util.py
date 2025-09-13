"""Utility functions for the BHyve integration."""

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt

from .const import CONF_DEVICES


def orbit_time_to_local_time(timestamp: str | None) -> datetime | None:
    """Convert the Orbit API timestamp to local time."""
    if timestamp is not None:
        parsed = dt.parse_datetime(timestamp)
        if parsed is not None:
            return dt.as_local(parsed)
    return None


def filter_configured_devices(entry: ConfigEntry, all_devices: list) -> list:
    """Filter the device list to those that are enabled in options."""
    filtered_devices = [
        d for d in all_devices if str(d["id"]) in entry.options[CONF_DEVICES]
    ]

    # Ensure that all devices have a name
    for device in filtered_devices:
        if device.get("name") is None:
            device["name"] = "Unknown Device"

    return filtered_devices
