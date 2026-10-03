DOMAIN = "ha_creality_ws"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_POWER_SWITCH = "power_switch"
CONF_POWER_SWITCH_ENABLED = "power_switch_enabled"
CONF_CAMERA_MODE = "camera_mode"
CONF_GO2RTC_URL = "go2rtc_url"
CONF_GO2RTC_PORT = "go2rtc_port"
CONF_CUSTOM_CAMERA_URL = "custom_camera_url"

DEFAULT_NAME = "Creality Printer (WS)"

# The live print card needs the companion app's Live Activity support, which
# arrived in this core release. Declared to HACS in hacs.json, and enforced at
# runtime as well: a manual or git install never goes through HACS, and would
# otherwise get a card that silently does not work.
MINIMUM_HA_VERSION = (2026, 7)

WS_PORT = 9999
MJPEG_PORT = 8080

WS_URL_TEMPLATE = "ws://{host}:" + str(WS_PORT)
# Subprotocol advertised by the printer's own web UI on the WebSocket handshake.
# Mirroring it (Sec-WebSocket-Protocol: wsslicer) keeps us byte-compatible with
# the official client. Per RFC 6455 the server ignores it if unsupported.
WS_SUBPROTOCOL = "wsslicer"
MJPEG_URL_TEMPLATE = "http://{host}:" + str(MJPEG_PORT) + "/?action=stream"

# WebRTC signaling endpoint (K2 family, and newer K1C firmwares)
WEBRTC_PORT = 8000
WEBRTC_CALL_ROOT_PATH = "/call"
WEBRTC_CALL_PATH = "/call/webrtc_local"
WEBRTC_CALL_ROOT_URL_TEMPLATE = "http://{host}:" + str(WEBRTC_PORT) + WEBRTC_CALL_ROOT_PATH
WEBRTC_URL_TEMPLATE = "http://{host}:" + str(WEBRTC_PORT) + WEBRTC_CALL_PATH

# Camera modes
CAM_MODE_AUTO = "auto"
CAM_MODE_MJPEG = "mjpeg"
CAM_MODE_WEBRTC = "webrtc"
CAM_MODE_WEBRTC_DIRECT = "webrtc_direct"
CAM_MODE_CUSTOM = "custom"

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

# go2rtc RTSP endpoint, used for HA's classic stream pipeline (HLS,
# camera.record, camera.play_stream, casting). HA's own managed go2rtc binary
# listens for RTSP on 127.0.0.1:18554 while its REST API is on 11984 (see
# homeassistant/components/go2rtc/server.py); a stand-alone go2rtc defaults to
# 8554. Users with a non-default RTSP port can override it in the options flow.
CONF_GO2RTC_RTSP_PORT = "go2rtc_rtsp_port"
# Custom-camera URL schemes that go2rtc ingests rather than Home Assistant
# fetching directly. A Custom source using one of these ends up on the same
# go2rtc camera as CAM_MODE_WEBRTC, so it needs the same settings.
GO2RTC_SOURCE_SCHEMES = ("rtsp", "rtmp", "srt")

HA_MANAGED_GO2RTC_RTSP_PORT = 18554
DEFAULT_GO2RTC_RTSP_PORT = 8554

# --- Sliced G-code metadata ------------------------------------------------- #
# The printer knows what the slicer estimated for the job it is running, but it
# never streams it. Asking for it returns `retGcodeFileInfo2`: metadata for
# *every* G-code file on the printer in one array, ~150 KiB for a couple of
# hundred files on a K1C. There is no single-file form of the query -- a
# filename, a full path, an object and other integer arguments all go
# unanswered -- so the whole listing is the only thing on offer, and it is far
# too big to poll or to keep in coordinator data. The coordinator matches the
# running job against it on arrival and stores that one entry here.
GCODE_FILE_REQUEST = "reqGcodeFile"
GCODE_FILE_RESPONSE = "retGcodeFileInfo2"
GCODE_INFO_KEY = "gcodeFileInfo"

# Re-asking is driven by the file name changing, not by a timer, because the
# metadata is static per file. These two only bound the failure case: a printer
# whose firmware does not answer `reqGcodeFile` at all must not be asked forever.
GCODE_INFO_RETRY_SECS = 30.0
GCODE_INFO_MAX_ATTEMPTS = 3

# Telemetry fields that gate entity creation and can only arrive once the printer
# is actually reachable. Platform setup does not wait for the printer (an offline
# printer must not block the config entry), so an entity depending on one of
# these would otherwise never be created until the next restart that happens to
# race the right way. The first appearance of any of them fires a discovery pass.
# targetBoxTemp is here because number.py gates the chamber control on it: a
# printer that reports a chamber target but never a maximum (K2 Base) would
# otherwise never fire a discovery pass, and the control would stay absent until
# a restart happened to race the right way -- the very defect this list exists
# to prevent.
# Must stay in step with every gate that reads these from coord.data:
# number.py promotes chamber *control* from the cached ModelDetection capability
# or a live targetBoxTemp -- never from maxBoxTemp, which K1-family printers
# report for a sensor-only chamber -- and sensor.py promotes the chamber *sensor*
# on boxTemp/targetBoxTemp/maxBoxTemp. maxBoxTemp stays in this list for that
# sensor gate. A field that gates an entity but does not appear here can never
# trigger the pass that would create it.
LATE_DISCOVERY_FIELDS: tuple[str, ...] = (
    "boxsInfo",
    "boxTemp",
    "maxBoxTemp",
    "targetBoxTemp",
    GCODE_INFO_KEY,
)

# Notifications
CONF_NOTIFY_DEVICE = "notify_device"
CONF_NOTIFY_COMPLETED = "notify_completed"
CONF_NOTIFY_ERROR = "notify_error"
CONF_NOTIFY_MINUTES_TO_END = "notify_minutes_to_end"
CONF_MINUTES_TO_END_VALUE = "minutes_to_end_value"

# Grace window after a (re)start during which the printer's current state is only
# captured as a baseline, never notified about. The printer keeps reporting the
# last job's file name and 100% progress indefinitely, so without this every HA
# restart fired a "print completed" notification (issue #112).
NOTIFY_PRIME_GRACE_SECS = 10.0

# Progress ceiling for re-arming the one-shot completion notification. The
# printer rounds progress up to 100 a second before the job actually ends and
# then reports 99 once more, so "progress fell below 100" on its own does not
# mean a new job started -- treating it that way sent the completion
# notification twice for every print. Only a drop clear of that jitter, or a
# restart of the job clock, counts as a new cycle.
NOTIFY_REARM_PROGRESS_MAX = 90

# How long a job has to stop looking like it is running before it is announced
# as stopped. Stopping a print does not announce itself in this telemetry (see
# `JobEndWatch`): what arrives is an ordinary-looking frame in a state the
# printer also reports while warming up, so the end is a transition that has to
# be held for a moment before it is believed. A single "idle" or "processing"
# frame mid-print is something this printer does, and it must not cost the user
# a "print stopped" notification.
#
# Only the ambiguous states wait. `state == 4` and a cleared file name are the
# printer saying so outright and are acted on at once.
NOTIFY_END_CONFIRM_SECS = 15.0

# --- Multi-target delivery -------------------------------------------------- #
# CONF_NOTIFY_DEVICE above held a single service name. It is still read, and is
# never deleted, so that rolling back to an earlier release keeps a user's
# target. coerce_targets() in notification_rules.py is the only thing that
# should look at it.
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_NOTIFY_LIVE = "notify_live"
CONF_NOTIFY_ACTIONS = "notify_actions"
CONF_NOTIFY_PREVIEW_IMAGE = "notify_preview_image"
CONF_NOTIFY_CAMERA_SNAPSHOT = "notify_camera_snapshot"
CONF_NOTIFY_TAP_PATH = "notify_tap_path"

# --- Custom notification text ----------------------------------------------- #
# One option per notification whose body this integration composes. Blank means
# "use the shipped, translated text", which is what every existing entry has, so
# the feature costs nothing until someone fills a field in.
#
# The keys are the notification names a user recognises from the toggles above
# rather than the internal EVENT_*/ALERT_* constants: these end up in
# strings.json and in a user's .storage, and renaming one later would silently
# drop their text.
CONF_NOTIFY_TEMPLATE_LIVE = "notify_template_live"
CONF_NOTIFY_TEMPLATE_COMPLETED = "notify_template_completed"
CONF_NOTIFY_TEMPLATE_STOPPED = "notify_template_stopped"
CONF_NOTIFY_TEMPLATE_SOON = "notify_template_soon"
CONF_NOTIFY_TEMPLATE_ERROR = "notify_template_error"
CONF_NOTIFY_TEMPLATE_RUNOUT = "notify_template_runout"

# Which notification each option overrides, keyed by the name the coordinator
# knows it by. Five of these are also strings.json keys, because that
# notification is one shipped sentence; "live" is not, its body being composed
# from several segments, and a template replaces the whole composition. Kept as
# one mapping so an option can never exist with nothing to apply to.
NOTIFY_TEMPLATE_OPTIONS = {
    "live": CONF_NOTIFY_TEMPLATE_LIVE,
    "completed": CONF_NOTIFY_TEMPLATE_COMPLETED,
    "stopped": CONF_NOTIFY_TEMPLATE_STOPPED,
    "finishing_soon": CONF_NOTIFY_TEMPLATE_SOON,
    "error": CONF_NOTIFY_TEMPLATE_ERROR,
    "filament_runout": CONF_NOTIFY_TEMPLATE_RUNOUT,
}

# Options only the notification path reads. A change confined to these is
# applied in place; anything else reloads the entry.
#
# A reload drops the WebSocket, flips every entity unavailable and restarts the
# camera stream. That is the right price for a new IP address or a different
# camera mode, and much too high for rewording a notification -- especially now
# that the options flow saves each page as it is submitted, so an evening spent
# tuning notification text used to cost a reload per page.
#
# `tools/tests/test_options_flow.py` checks this against the fields the
# notifications page actually renders, so a new option cannot be added to that
# page without deciding which side of this line it falls on.
NOTIFY_ONLY_OPTION_KEYS = frozenset(
    {
        CONF_NOTIFY_DEVICE,
        CONF_NOTIFY_TARGETS,
        CONF_NOTIFY_LIVE,
        CONF_NOTIFY_ACTIONS,
        CONF_NOTIFY_PREVIEW_IMAGE,
        CONF_NOTIFY_CAMERA_SNAPSHOT,
        CONF_NOTIFY_TAP_PATH,
        CONF_NOTIFY_COMPLETED,
        CONF_NOTIFY_ERROR,
        CONF_NOTIFY_MINUTES_TO_END,
        CONF_MINUTES_TO_END_VALUE,
    }
    | set(NOTIFY_TEMPLATE_OPTIONS.values())
)

# Sentinel message that dismisses a notification (and ends a Live Activity)
# carrying the same tag. It is only meaningful to the companion app: any other
# notify platform would render it as visible body text, so it must never be
# delivered to one.
CLEAR_NOTIFICATION_MARKER = "clear_notification"

# --- Live print card -------------------------------------------------------- #
# Progress here is authoritative 0-100, not an estimate, so pushes are driven by
# a monotonic milestone latch rather than a cap derived from the expected
# duration. A print then costs at most 100/STEP progress pushes whether it runs
# twenty minutes or forty hours, and the end-of-print 99->100->99->100 jitter
# (see NOTIFY_REARM_PROGRESS_MAX) cannot produce a second push.
# Every whole percent. The step used to be 5, which is what made the card
# visibly jump 15 -> 20 -> 25 while the printer was reporting every value in
# between. Progress is 0-100, so this bounds a job at ~100 progress pushes
# however long it runs -- inside the relay's 500-per-device-per-day budget for
# roughly four prints a day, and the floor below keeps a fast print from
# spending them all at once.
NOTIFY_LIVE_MILESTONE_STEP = 1
# The refresh cadence. Progress and the remaining estimate both move
# continuously, and a milestone latch on its own left the card reading a stale
# percentage for as long as it took to gain 5% -- twenty minutes or more on a
# long print. So the card refreshes on a wall clock instead, and the milestone
# only forces an *early* refresh when progress has moved a lot in little time.
#
# 300s is chosen against a hard external limit rather than taste: the companion
# push relay allows 500 notifications per device per day (visible in its own
# rate-limit log line). One printer at this cadence spends 12 an hour, so even a
# 40-hour print stays inside the budget with room for a second printer.
NOTIFY_LIVE_INTERVAL_SECS = 300.0
# Floor under everything, including a forced refresh. Telemetry arrives several
# times a second, so this is what stops a frame storm becoming a push storm.
NOTIFY_LIVE_MIN_INTERVAL_SECS = 30.0
# Pause and resume are deliberate user actions and must show up at once, so a
# state change bypasses both intervals above. Safe because `decide()` requires
# the derived state to have actually *changed*: a printer sitting in one state
# cannot retrigger it, and only genuine flapping could, which is a printer
# fault rather than something to paper over with a delay.
NOTIFY_LIVE_TRANSITION_FLOOR_SECS = 0.0
# Circuit breaker for pathological telemetry, not a design limit: at the
# cadence above this is ~50 hours of printing, comfortably past any real job,
# and the relay's own daily budget is the real ceiling.
NOTIFY_LIVE_MAX_PUSHES_PER_JOB = 600
# Apple hard-expires a Live Activity after eight hours. Past this the live-only
# keys are dropped and the card degrades to a plain tagged notification, which
# still updates in place. Android 16 progress notifications do not expire, so
# this is an iOS-shaped limit we accept rather than work around -- restarting
# the activity would burn a push-to-start slot and show a visibly new card.
NOTIFY_LIVE_IOS_EXPIRY_SECS = 28800.0
# No telemetry for this long means the printer is gone; clear the card.
NOTIFY_LIVE_STALE_CLEAR_SECS = 90.0

# Card colours by phase.
NOTIFY_COLOR_PRINTING = "#03a9f4"
NOTIFY_COLOR_PAUSED = "#ffa726"
NOTIFY_COLOR_DONE = "#43a047"
NOTIFY_COLOR_ERROR = "#e53935"

# Android notification channel *names* are user-visible in the phone's settings,
# so they live in strings.json like every other label. Splitting the terminal
# and alert channels from the live one lets a user silence progress without
# silencing failures.
NOTIFY_CHANNEL_KEY_LIVE = "channel_live"
NOTIFY_CHANNEL_KEY_DONE = "channel_finished"
NOTIFY_CHANNEL_KEY_ALERT = "channel_alerts"
# The "finishing soon" reminder is its own channel because it is the one
# progress-related notification that should be able to make a sound while the
# live card stays silent -- the whole point of it is to catch someone's
# attention before the print ends.
NOTIFY_CHANNEL_KEY_SOON = "channel_soon"

# Joins the segments of a live-card body. Punctuation rather than prose, so it
# stays here instead of in strings.json. A hyphen rather than a middot: the
# middot renders as a hollow box in some Android notification fonts, and the
# body is three short numbers that need separating, not a typographic list.
NOTIFY_BODY_SEPARATOR = " - "

# `preview_reason` values that mean the image entity would serve its 1x1
# placeholder. Anything else -- including an unset value, which just means
# nothing has asked the entity for bytes yet -- is worth attaching.
PREVIEW_REASONS_UNUSABLE = ("not_printing", "fetch_failed")

# --- Bus events ------------------------------------------------------------- #
# Language-neutral, and fired whether or not any notify target is configured.
# Notification bodies are composed in Python and therefore follow the *server*
# language -- an integration is never told which user a notify call is for --
# so these are the supported way to build your own text, in your own language,
# with your own conditions.
BUS_EVENT_PRINT_STARTED = "ha_creality_ws_print_started"
BUS_EVENT_PRINT_FINISHED = "ha_creality_ws_print_finished"
BUS_EVENT_PRINT_STOPPED = "ha_creality_ws_print_stopped"
BUS_EVENT_PRINT_ERROR = "ha_creality_ws_print_error"

CONF_POLLING_RATE = "polling_rate"
DEFAULT_POLLING_RATE = 0  # Real-time

# Moonraker defaults
MR_PORT = 7125
MR_POLL_INTERVAL = 30
MR_POLL_TIMEOUT = 5
MR_QUERY_PARAMS = "objects=temperature_fan%20chamber_fan"
