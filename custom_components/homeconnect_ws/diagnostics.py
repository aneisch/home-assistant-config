"""Diagnostics support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_DEVICE_ID

from .const import CONF_AES_IV, CONF_PSK

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import HCConfigEntry

TO_REDACT = [CONF_PSK, CONF_AES_IV, CONF_DEVICE_ID, "serialNumber", "deviceID", "shipSki", "mac"]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: HCConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "appliance_state": entry.runtime_data.appliance.dump(),
    }
