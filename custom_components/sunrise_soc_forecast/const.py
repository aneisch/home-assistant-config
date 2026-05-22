"""Constants for Sunrise SoC Forecast integration."""

DOMAIN = "sunrise_soc_forecast"

# Increment this when calculation logic changes to invalidate stale frozen data
STORAGE_VERSION = 4

# Config keys
CONF_MAIN_SOC_ENTITY = "main_soc_entity"
CONF_MAIN_POWER_ENTITY = "main_power_entity"
CONF_MAIN_CAPACITY = "main_capacity"
CONF_MAIN_FLOOR = "main_floor"

CONF_BACKUP_ENABLED = "backup_enabled"
CONF_BACKUP_SOC_ENTITY = "backup_soc_entity"
CONF_BACKUP_DISCHARGE_ENTITY = "backup_discharge_entity"
CONF_BACKUP_CAPACITY = "backup_capacity"
CONF_BACKUP_FLOOR = "backup_floor"
CONF_BACKUP_DISCHARGE_KW = "backup_discharge_kw"
CONF_BACKUP_ACTIVATION_HOUR = "backup_activation_hour"
CONF_BACKUP_MODE = "backup_mode"
CONF_BACKUP_CHARGE_EFFICIENCY = "backup_charge_efficiency"
CONF_BACKUP_DISCHARGE_EFFICIENCY = "backup_discharge_efficiency"

# Backup deployment modes
BACKUP_MODE_ALWAYS = "always"
BACKUP_MODE_TARGET = "target_based"

CONF_DEFAULT_DAILY = "default_daily"
CONF_DEFAULT_OVERNIGHT = "default_overnight"
CONF_GUARD_THRESHOLD = "guard_threshold"

CONF_SOLCAST_REMAINING = "solcast_remaining_today"
CONF_SOLCAST_FORECAST_TODAY = "solcast_forecast_today"
CONF_SOLCAST_TOMORROW = "solcast_tomorrow"
CONF_SOLCAST_DAY_3 = "solcast_day_3"
CONF_SOLCAST_DAY_4 = "solcast_day_4"
CONF_SOLCAST_DAY_5 = "solcast_day_5"
CONF_SOLCAST_DAY_6 = "solcast_day_6"
CONF_SOLCAST_DAY_7 = "solcast_day_7"

CONF_MAIN_INVERTER_EFFICIENCY = "main_inverter_efficiency"
CONF_GRID_POWER_ENTITY = "grid_power_entity"

# Solar forecast source
CONF_SOLAR_SOURCE = "solar_source"
CONF_SOLAR_CONFIG_ENTRY = "solar_config_entry"
SOLAR_SOURCE_SOLCAST = "solcast"
SOLAR_SOURCE_OPEN_METEO = "open_meteo"
SOLAR_SOURCE_MANUAL = "manual"

# Known solar forecast integration domains
SOLAR_DOMAINS = {
    "solcast_solar": SOLAR_SOURCE_SOLCAST,
    "open_meteo_solar_forecast": SOLAR_SOURCE_OPEN_METEO,
}

# Auto-discovered solar entity config keys (stored after discovery)
CONF_SOLAR_ENTITY_REMAINING = "solar_entity_remaining"
CONF_SOLAR_ENTITY_TODAY = "solar_entity_today"
CONF_SOLAR_ENTITY_TOMORROW = "solar_entity_tomorrow"
CONF_SOLAR_ENTITY_DAY_3 = "solar_entity_day_3"
CONF_SOLAR_ENTITY_DAY_4 = "solar_entity_day_4"
CONF_SOLAR_ENTITY_DAY_5 = "solar_entity_day_5"
CONF_SOLAR_ENTITY_DAY_6 = "solar_entity_day_6"
CONF_SOLAR_ENTITY_DAY_7 = "solar_entity_day_7"

# Mapping day number → auto-discovered config key
SOLAR_DAY_MAP = {
    1: CONF_SOLAR_ENTITY_TODAY,
    2: CONF_SOLAR_ENTITY_TOMORROW,
    3: CONF_SOLAR_ENTITY_DAY_3,
    4: CONF_SOLAR_ENTITY_DAY_4,
    5: CONF_SOLAR_ENTITY_DAY_5,
    6: CONF_SOLAR_ENTITY_DAY_6,
    7: CONF_SOLAR_ENTITY_DAY_7,
}

CONF_FORECAST_DAYS = "forecast_days"
CONF_TARGET_SOC = "target_soc"

# Dump load configuration
# Stored as list[dict] under CONF_DUMP_LOADS in entry.data/options.
# Each item has: name, type (manual|sensor), and type-specific fields.
CONF_DUMP_LOADS = "dump_loads"
DUMP_LOAD_TYPE_MANUAL = "manual"
DUMP_LOAD_TYPE_SENSOR = "sensor"

CONF_DUMP_LOAD_NAME = "name"
CONF_DUMP_LOAD_TYPE = "type"
# Manual mode (simple): average kW + start/end hour window
CONF_DUMP_LOAD_AVG_KW = "avg_kw"
CONF_DUMP_LOAD_START_HOUR = "start_hour"
CONF_DUMP_LOAD_END_HOUR = "end_hour"
# Manual mode (advanced): explicit 24-element kW profile
CONF_DUMP_LOAD_HOURLY_PROFILE = "hourly_profile"
CONF_DUMP_LOAD_ADVANCED = "advanced"
# Sensor mode: power entity (W), integrated by coordinator
CONF_DUMP_LOAD_POWER_ENTITY = "power_entity"

DEFAULT_DUMP_LOAD_AVG_KW = 1.0
DEFAULT_DUMP_LOAD_START_HOUR = 9
DEFAULT_DUMP_LOAD_END_HOUR = 16

# Defaults
DEFAULT_MAIN_CAPACITY = 128.0
DEFAULT_MAIN_FLOOR = 5.0
DEFAULT_BACKUP_CAPACITY = 16.0
DEFAULT_BACKUP_FLOOR = 5.0
DEFAULT_BACKUP_DISCHARGE_KW = 6.0
DEFAULT_BACKUP_ACTIVATION_HOUR = 2
DEFAULT_DAILY_CONSUMPTION = 128.0
DEFAULT_OVERNIGHT_CONSUMPTION = 64.0
DEFAULT_GUARD_THRESHOLD = 3.0
DEFAULT_FORECAST_DAYS = 7
DEFAULT_TARGET_SOC = 20.0
DEFAULT_MAIN_INVERTER_EFFICIENCY = 94.0
DEFAULT_BACKUP_CHARGE_EFFICIENCY = 92.0
DEFAULT_BACKUP_DISCHARGE_EFFICIENCY = 98.0

# Solcast standard mapping: day -> config key
SOLCAST_STANDARD = {
    2: CONF_SOLCAST_TOMORROW,
    3: CONF_SOLCAST_DAY_3,
    4: CONF_SOLCAST_DAY_4,
    5: CONF_SOLCAST_DAY_5,
    6: CONF_SOLCAST_DAY_6,
    7: CONF_SOLCAST_DAY_7,
}

# Solcast shifted mapping (post-midnight): day -> config key
SOLCAST_SHIFTED = {
    2: CONF_SOLCAST_REMAINING,
    3: CONF_SOLCAST_TOMORROW,
    4: CONF_SOLCAST_DAY_3,
    5: CONF_SOLCAST_DAY_4,
    6: CONF_SOLCAST_DAY_5,
    7: CONF_SOLCAST_DAY_6,
}
