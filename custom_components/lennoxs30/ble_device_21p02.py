"""Lennox BLE Air Quality Sensor."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.helpers.entity import EntityCategory

lennox_21p02_sensors = [
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
        "input_id": 4100,
        "status_id": 4102,
        "name": "pm25",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PM25,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    },
    {
        "input_id": 4103,
        "status_id": 4104,
        "name": "co2",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.CO2,
        "uom": CONCENTRATION_PARTS_PER_MILLION,
    },
    {
        "input_id": 4105,
        "status_id": 4106,
        "name": "voc",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "precision": 2,
    },
]

lennox_21p02_binary_sensors = [
    {"input_id": 4001, "name": "alarm_status", "entity_category": EntityCategory.DIAGNOSTIC},
    {"input_id": 4002, "name": "device_state", "entity_category": EntityCategory.DIAGNOSTIC},
    {"input_id": 4107, "name": "idle_switch", "entity_category": EntityCategory.DIAGNOSTIC},
]

lennox_iaq_sensors = [
    {
        "input": "iaq_mitigation_action",
        "name": "mitigation action",
    },
    {
        "input": "iaq_mitigation_state",
        "name": "mitigation state",
    },
    {
        "input": "iaq_overall_index",
        "name": "overall index",
    },
    {
        "input": "iaq_pm25_sta",
        "status": "iaq_pm25_sta_valid",
        "name": "pm25 sta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PM25,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "precision": 4,
    },
    {
        "input": "iaq_pm25_lta",
        "status": "iaq_pm25_lta_valid",
        "name": "pm25 lta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.PM25,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "precision": 4,
    },
    {
        "input": "iaq_pm25_component_score",
        "name": "pm25 component score",
    },
    {
        "input": "iaq_voc_sta",
        "status": "iaq_voc_sta_valid",
        "name": "voc sta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "precision": 2,
    },
    {
        "input": "iaq_voc_lta",
        "status": "iaq_voc_lta_valid",
        "name": "voc lta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "precision": 2,
    },
    {
        "input": "iaq_voc_component_score",
        "name": "voc component score",
    },
    {
        "input": "iaq_co2_lta",
        "status": "iaq_co2_lta_valid",
        "name": "co2 lta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.CO2,
        "uom": CONCENTRATION_PARTS_PER_MILLION,
        "precision": 1,
    },
    {
        "input": "iaq_co2_sta",
        "status": "iaq_co2_sta_valid",
        "name": "co2 sta",
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.CO2,
        "uom": CONCENTRATION_PARTS_PER_MILLION,
        "precision": 1,
    },
    {
        "input": "iaq_co2_component_score",
        "name": "co2 component score",
    },
]
