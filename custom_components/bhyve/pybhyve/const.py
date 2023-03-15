"""Define constants for the BHyve component."""
API_HOST = "https://api.orbitbhyve.com"
WS_HOST = "wss://api.orbitbhyve.com/v1/events"

LOGIN_PATH = "/v1/session"
DEVICES_PATH = "/v1/devices"
DEVICE_HISTORY_PATH = "/v1/watering_events/{}"
TIMER_PROGRAMS_PATH = "/v1/sprinkler_timer_programs"
LANDSCAPE_DESCRIPTIONS_PATH = "/v1/landscape_descriptions"

API_POLL_PERIOD = 300
