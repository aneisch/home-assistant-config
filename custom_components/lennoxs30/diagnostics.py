"""Diagnostics support for LennoxS30."""

# pylint: disable=line-too-long
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import MANAGER, Manager
from .const import LENNOX_DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager: Manager = hass.data[LENNOX_DOMAIN][config_entry.unique_id][MANAGER]
    data: dict[str, Any] = {}

    data["config"] = {}
    for key, val in config_entry.data.items():
        data["config"][key] = val
    if CONF_PASSWORD in data["config"]:
        data["config"][CONF_PASSWORD] = "**redacted**"
    if CONF_EMAIL in data["config"]:
        data["config"][CONF_EMAIL] = "**redacted**"
    data["system"] = {}
    for system in manager.api.system_list:
        system_data: dict[str, any] = {
            "relayServer": system.relayServerConnected,
            "internet": system.internetStatus,
            "diagLevel": system.diagLevel,
            "cloud_status": system.cloud_status,
            "productType": system.productType,
            "sibling_identifier": {sibling.sibling_identifier for sibling in system.siblings},
            "sibling_ip": {sibling.sibling_ipAddress for sibling in system.siblings},
            "softwareVersion": system.softwareVersion,
            "sysUpTime": system.sysUpTime,
        }

        system_data["equipment"] = {}
        for eq_id, equipment in system.equipment.items():
            element = {
                "name": equipment.equipment_name,
                "eqType": equipment.equipType,
                "eqTypeName": equipment.equipment_type_name,
                "model": equipment.unit_model_number,
            }
            system_data["equipment"][eq_id] = element

        system_data["reminders"] = {}
        for reminder_id, reminder in system.reminders.items():
            system_data["reminders"][reminder_id] = {
                "kind": reminder.kind,
                "expiry_type": reminder.expiry_type,
                "enabled": reminder.enabled,
                "is_valid": reminder.is_valid,
                "expired": reminder.expired,
                "remaining_pct": reminder.remaining_pct,
                "reminder_time": reminder.reminder_time,
            }
        data["system"][system.sysId] = system_data

    data["comm_metrics"] = manager.getMetricsList()
    return data
