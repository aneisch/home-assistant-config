"""Support for Lennox BLE Remote Sensor."""

# pylint: disable=line-too-long
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.entity import EntityCategory

lennox_22v25_sensors = [
    {
        "input_id": 4000,
        "name": "rssi",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "entity_category": EntityCategory.DIAGNOSTIC,
        "uom": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    },
    {
        "input_id": 4003,
        "name": "total powered time",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.DURATION,
        "entity_category": EntityCategory.DIAGNOSTIC,
    },
    {
        "input_id": 4004,
        "name": "ble rssi",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "entity_category": EntityCategory.DIAGNOSTIC,
        "uom": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    },
    {
        "input_id": 4050,
        "status_id": 4051,
        "name": "temperature",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "input_id": 4052,
        "status_id": 4053,
        "name": "humidity",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.HUMIDITY,
    },
    {
        "input_id": 4054,
        "status_id": 4055,
        "name": "battery",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.BATTERY,
        "entity_category": EntityCategory.DIAGNOSTIC,
    },
    {
        "input_id": 4058,
        "status_id": 4059,
        "name": "digital temperature",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
    {
        "input_id": 4060,
        "status_id": 4061,
        "name": "analog temperature",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.TEMPERATURE,
    },
]

lennox_22v25_binary_sensors = [
    {"input_id": 4001, "name": "alarm_status", "entity_category": EntityCategory.DIAGNOSTIC},
    {"input_id": 4002, "name": "device_state", "entity_category": EntityCategory.DIAGNOSTIC},
    {"input_id": 4056, "status_id": 4057, "name": "occupancy", "device_class": BinarySensorDeviceClass.OCCUPANCY},
]
