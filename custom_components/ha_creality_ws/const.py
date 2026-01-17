DOMAIN = "ha_creality_ws"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_DISCOVERY_SCAN_CIDR = "scan_cidr"
CONF_POWER_SWITCH = "power_switch"
CONF_POWER_SWITCH_ENABLED = "power_switch_enabled"
CONF_CAMERA_MODE = "camera_mode"
CONF_GO2RTC_URL = "go2rtc_url"
CONF_GO2RTC_PORT = "go2rtc_port"

DEFAULT_NAME = "Creality Printer (WS)"

WS_PORT = 9999
MJPEG_PORT = 8080
HTTP_PORT = 80

WS_URL_TEMPLATE = "ws://{host}:" + str(WS_PORT)
MJPEG_URL_TEMPLATE = "http://{host}:" + str(MJPEG_PORT) + "/?action=stream"

# WebRTC signaling endpoint (K2 models)
WEBRTC_PORT = 8000
WEBRTC_CALL_PATH = "/call/webrtc_local"
WEBRTC_URL_TEMPLATE = "http://{host}:" + str(WEBRTC_PORT) + WEBRTC_CALL_PATH

# Camera modes
CAM_MODE_AUTO = "auto"
CAM_MODE_MJPEG = "mjpeg"
CAM_MODE_WEBRTC = "webrtc"

MFR = "Creality"
MODEL = "K"

# ---- Health / reconnect / keepalive ----
STALE_AFTER_SECS = 15
RETRY_MIN_BACKOFF = 1.0
RETRY_MAX_BACKOFF = 300.0
RETRY_BACKOFF_MULTIPLIER = 1.8
HEARTBEAT_SECS = 10.0
PROBE_ON_SILENCE_SECS = 10.0

# go2rtc defaults
DEFAULT_GO2RTC_URL = "localhost"
DEFAULT_GO2RTC_PORT = 11984

# Notifications
CONF_NOTIFY_DEVICE = "notify_device"
CONF_NOTIFY_COMPLETED = "notify_completed"
CONF_NOTIFY_ERROR = "notify_error"
CONF_NOTIFY_MINUTES_TO_END = "notify_minutes_to_end"
CONF_MINUTES_TO_END_VALUE = "minutes_to_end_value"

CONF_POLLING_RATE = "polling_rate"
DEFAULT_POLLING_RATE = 0  # Real-time