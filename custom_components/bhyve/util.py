"""Utility functions for the BHyve integration."""

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt

from .const import CONF_DEVICES, DEVICE_BRIDGE

# Orbit returns ~2106-02-07 (epoch max) as a sentinel for "nothing scheduled".
# Treat any timestamp from this year on as that sentinel.
_NEXT_WATERING_SENTINEL_YEAR = 2100


def rain_delay_active(status: dict) -> bool:
    """Return True when the device status has a rain delay in force."""
    return (status.get("rain_delay") or 0) > 0


def next_watering_time(status: dict) -> datetime | None:
    """
    Return the device's next watering time, or None when it is known to be wrong.

    Orbit only refreshes next_start_time on the 5-minute poll, and does not
    always clear it, so hide it when (#430):
    - a rain delay is active, since Orbit won't water through it;
    - it is Orbit's "nothing scheduled" sentinel;
    - it is in the past, e.g. the skipped run just after a rain delay ends.
    """
    if rain_delay_active(status):
        return None

    next_start = orbit_time_to_local_time(status.get("next_start_time"))
    if next_start is None or next_start.year >= _NEXT_WATERING_SENTINEL_YEAR:
        return None
    if next_start <= dt.now():
        return None
    return next_start


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
