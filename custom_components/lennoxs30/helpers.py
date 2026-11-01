"""SHelper functins."""

# pylint: disable=logging-not-lazy
# pylint: disable=logging-fstring-interpolation
# pylint: disable=global-statement
# pylint: disable=broad-except
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=invalid-name
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from lennoxs30api import lennox_system, lennox_zone
from lennoxs30api.lennox_equipment import lennox_equipment, lennox_equipment_parameter

from .const import LENNOX_DOMAIN

if TYPE_CHECKING:
    from . import Manager

_LOGGER = logging.getLogger(__name__)


def lennox_uom_to_ha_uom(unit: str) -> str:
    """Convert Lennox UOM to a HASS UOM."""
    if unit in ("F", "Fahreheit"):
        return UnitOfTemperature.FAHRENHEIT
    if unit in ("C", "Celsius"):
        return UnitOfTemperature.CELSIUS  # Not validated - do no know if European Units report
    if unit == "CFM":
        return UnitOfVolumeFlowRate.CUBIC_FEET_PER_MINUTE
    if unit == "min":
        return UnitOfTime.MINUTES
    if unit in ("sec", "Sec"):
        return UnitOfTime.SECONDS
    if unit == "%":
        return PERCENTAGE
    if unit == "Hz":
        return UnitOfFrequency.HERTZ
    if unit == "V":
        return UnitOfElectricPotential.VOLT
    if unit == "A":
        return UnitOfElectricCurrent.AMPERE
    if unit in ("", "none"):
        return None
    return unit


def helper_get_equipment_device_info(manager: "Manager", system: lennox_system, equipment_id: int) -> dict:
    """Construct the HASS device info for an entity."""
    equip_device_map = manager.system_equip_device_map.get(system.sysId)
    if equip_device_map is not None:
        device = equip_device_map.get(equipment_id)
        if device is not None:
            return {
                "identifiers": {(LENNOX_DOMAIN, device.unique_name)},
            }
        _LOGGER.warning(
            "helper_get_equipment_device_info Unable to find equipment_id [%s] in device map sysId [%s], please raise an issue",
            equipment_id,
            system.sysId,
        )
    else:
        _LOGGER.error(
            "helper_get_equipment_device_info No equipment device map found for sysId [%s] equipment_id [%s], please raise an issue",
            system.sysId,
            equipment_id,
        )
    return {
        "identifiers": {(LENNOX_DOMAIN, system.unique_id)},
    }


def helper_create_equipment_entity_name(system: lennox_system, equipment: lennox_equipment, name: str, prefix: str | None = None) -> str:
    """Create a name for the entity."""
    suffix = str(equipment.equipment_name)
    if equipment.equipment_id == 1:
        suffix = "ou"
    elif equipment.equipment_id == 2:
        suffix = "iu"
    elif equipment.equipment_id == 0:
        suffix = None

    result: str = system.name

    if prefix is not None:
        result = result + "_" + prefix

    if suffix is not None:
        result = result + "_" + suffix

    result = result + "_" + name

    return result.replace(" ", "_").replace("-", "").replace(".", "").replace("__", "_")


def helper_create_system_unique_id(system: lennox_system, suffix: str) -> str:
    """Construct a unique name for a system entity."""
    result = system.unique_id + suffix
    return result.replace(" ", "_").replace("-", "").replace(".", "").replace("__", "_")


def helper_create_zone_entity_name(system: lennox_system, zone: lennox_zone) -> str:
    """Create a stable name for zone entities and zone devices."""
    system_name: str = ""
    if system.name is not None:
        system_name = str(system.name).strip()
    if system_name == "":
        system_name = f"system_{system.sysId}"

    zone_name: str = ""
    if zone.name is not None:
        zone_name = str(zone.name).strip()
    if zone_name == "":
        zone_name = f"Zone_{zone.id}"

    return f"{system_name}_{zone_name}"


def helper_get_parameter_extra_attributes(equipment: lennox_equipment, parameter: lennox_equipment_parameter) -> dict[str, Any]:
    """Construct extra attributes for equipment."""
    attrs: dict[str, Any] = {}
    attrs["equipment_id"] = equipment.equipment_id
    attrs["equipment_type_id"] = equipment.equipType
    attrs["parameter_id"] = parameter.pid
    return attrs
