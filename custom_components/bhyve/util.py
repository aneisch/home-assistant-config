"""Utility functions for the BHyve integration."""

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt

from .const import CONF_DEVICES, DEVICE_BRIDGE


def orbit_time_to_local_time(timestamp: str | None) -> datetime | None:
    """Convert the Orbit API timestamp to local time."""
    if timestamp is not None:
        parsed = dt.parse_datetime(timestamp)
        if parsed is not None:
            return dt.as_local(parsed)
    return None


def filter_configured_devices(entry: ConfigEntry, all_devices: list) -> list:
    """
    Filter the device list to those that are enabled in options.

    Bridge devices are always included since they are not user-selectable
    but are needed to register the hub in Home Assistant.
    """
    configured_devices = entry.options.get(CONF_DEVICES, [])
    filtered_devices = [
        d
        for d in all_devices
        if str(d["id"]) in configured_devices or d.get("type") == DEVICE_BRIDGE
    ]

    # Ensure that all devices have a name
    for device in filtered_devices:
        if device.get("name") is None:
            device["name"] = "Unknown Device"

    return filtered_devices
