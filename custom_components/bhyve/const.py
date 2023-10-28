"""Define constants for the BHyve component."""
DOMAIN = "bhyve"
MANUFACTURER = "Orbit BHyve"

DEVICES = "devices"
PROGRAMS = "programs"

DATA_BHYVE = "bhyve_data"

CONF_CLIENT = "client"
CONF_DEVICES = "devices"

DEVICE_BRIDGE = "bridge"
DEVICE_SPRINKLER = "sprinkler_timer"
DEVICE_FLOOD = "flood_sensor"

EVENT_BATTERY_STATUS = "battery_status"
EVENT_CHANGE_MODE = "change_mode"
EVENT_DEVICE_IDLE = "device_idle"
EVENT_FS_ALARM = "fs_status_update"
EVENT_PROGRAM_CHANGED = "program_changed"
EVENT_RAIN_DELAY = "rain_delay"
EVENT_SET_MANUAL_PRESET_TIME = "set_manual_preset_runtime"
EVENT_WATERING_COMPLETE = "watering_complete"
EVENT_WATERING_IN_PROGRESS = "watering_in_progress_notification"

SIGNAL_UPDATE_DEVICE = "bhyve_update_device_{}"
SIGNAL_UPDATE_PROGRAM = "bhyve_update_program_{}"

TYPE_BINARY_SENSOR = "binary_sensor"
TYPE_SENSOR = "sensor"
