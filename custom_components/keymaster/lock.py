"""Lock class."""
from dataclasses import dataclass
from typing import Optional

from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_registry import EntityRegistry


@dataclass
class KeymasterLock:
    """Class to represent a keymaster lock."""

    lock_name: str
    lock_entity_id: str
    alarm_level_or_user_code_entity_id: Optional[str]
    alarm_type_or_access_control_entity_id: Optional[str]
    ent_reg: EntityRegistry
    door_sensor_entity_id: Optional[str] = None
    zwave_js_lock_node = None
    zwave_js_lock_device: DeviceEntry = None
    parent: Optional[str] = None
