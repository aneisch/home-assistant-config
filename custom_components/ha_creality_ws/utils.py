from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any, ClassVar

__all__ = [
    "coerce_numbers",
    "parse_model_version",
    "parse_position",
    "safe_float",
    "normalize_color_hex",
    "format_filament_label",
    "build_spool_key",
    "derive_print_state",
    "BUSY_PRINT_STATES",
    "PRINT_STATES",
    "MaterialValueError",
    "build_modify_material_payload",
    "normalize_material_color",
]


# A number written the way the printer writes one: "31.030000", "0", "-2.5".
# Not "007" or " 42": a leading zero or padding means an identifier that only
# looks numeric, and int() would quietly strip it (R66).
_NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")


def coerce_numbers(d: dict[str, Any]) -> dict[str, Any]:
    """Convert numeric strings in a dict to numbers where safe."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str) and _NUMBER_RE.fullmatch(v):
            out[k] = float(v) if "." in v else int(v)
            continue
        out[k] = v
    return out


def parse_model_version(s: str | None) -> tuple[str | None, str | None]:
    """Extract HW/SW versions from a semi-structured string (Creality format)."""
    if not s or not isinstance(s, str):
        return (None, None)

    parts: dict[str, str | None] = {}
    for seg in s.split(";"):
        seg = seg.strip()
        if not seg or ":" not in seg:
            continue
        k, v = seg.split(":", 1)
        parts[k.strip().lower()] = (v.strip() or None)

    # Try printer versions first, then DWIN versions as fallback
    hw = parts.get("printer hw ver")
    sw = parts.get("printer sw ver")
    
    # If printer versions are empty or just whitespace, use DWIN versions (prefixed with "DWIN")
    if not hw or hw.strip() == "":
        hw = parts.get("dwin hw ver")
        if hw:
            hw = f"DWIN {hw}"
    
    if not sw or sw.strip() == "":
        sw = parts.get("dwin sw ver")
        if sw:
            sw = f"DWIN {sw}"
    
    return (hw, sw)


_POS_RE = re.compile(r"X:(?P<X>-?\d+(?:\.\d+)?)\s+Y:(?P<Y>-?\d+(?:\.\d+)?)\s+Z:(?P<Z>-?\d+(?:\.\d+)?)")


def parse_position(d: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    raw = d.get("curPosition")
    if not isinstance(raw, str):
        return (None, None, None)
    m = _POS_RE.search(raw)
    if not m:
        return (None, None, None)
    try:
        return (float(m.group("X")), float(m.group("Y")), float(m.group("Z")))
    except Exception:
        return (None, None, None)


def safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def numeric_state(v: Any) -> int | float | None:
    """A telemetry value as a numeric sensor state, or None.

    Home Assistant rejects a numeric sensor's state write outright when the
    value is not a number, and the entity then keeps whatever state it had,
    which after a power-on is "unavailable". Printers send blanks (`""`) for
    some fields while booting (#121), and the client's cumulative state keeps
    the blank until the key is sent again, so one blank frame used to strand
    a sensor for minutes. NaN and infinities are refused for the same reason.

    An int stays an int: a layer count that became `128.0` would change the
    entity's state string.
    """
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, str):
        text = v.strip()
        if not text:
            return None
        try:
            num = float(text)
        except ValueError:
            return None
        if not math.isfinite(num):
            return None
        if num.is_integer() and not any(c in text for c in ".eE"):
            return int(num)
        return num
    return None
def _is_routable_v4(addr: Any) -> bool:
    """An IPv4 address that is not link-local (169.254.0.0/16)."""
    text = str(addr).strip()
    if not text or ":" in text:
        return False
    return not text.startswith("169.254.")


def extract_info_from_zeroconf(info: Any) -> tuple[str | None, str | None]:
    """Extract host/IP and optional MAC from zeroconf discovery info.
    
    Returns:
        (host, mac) tuple. MAC is normalized to uppercase AA:BB:CC... or None.
    """
    host: str | None = None
    mac: str | None = None
    
    if isinstance(info, dict):
        # Extract Host
        h_raw = info.get("host")
        if h_raw:
            host = str(h_raw)
        else:
            addrs_raw = info.get("addresses") or info.get("ip_addresses") or info.get("ip_address")
            if isinstance(addrs_raw, (list, tuple)) and addrs_raw:
                # IPv4 first (no ':' in the string), and a routable IPv4 ahead of
                # a 169.254 link-local one. A printer whose DHCP lease failed, or
                # which answers on a second interface, advertises the link-local
                # address alongside the real one -- and taking whichever came
                # first meant `async_step_zeroconf` probed an address nothing
                # answers on and aborted with "not_K", so the printer was never
                # offered at all. Link-local is still used if it is all there is.
                host = str(
                    next((a for a in addrs_raw if _is_routable_v4(a)), None)
                    or next((a for a in addrs_raw if ":" not in str(a)), None)
                    or addrs_raw[0]
                )
            elif isinstance(addrs_raw, str):
                host = addrs_raw
            if not host:
                hn = info.get("hostname")
                if isinstance(hn, str):
                    host = hn.strip(".")

        # Extract MAC from properties
        props = info.get("properties", {})
        if props:
            # Look for common MAC keys
            for k in ("mac", "device_mac", "serial"):
                val = props.get(k)
                if val:
                    # Basic MAC validation/normalization could go here
                    if ":" in str(val) or len(str(val)) >= 12:
                        mac = str(val).upper()
                        break
        
        # Fallback: Extract MAC from hostname if structured like "K1-AABBCC" ?
        # Not reliable enough without more knowledge.
        return (host, mac)

    # Object style (HA ZeroconfServiceInfo)
    try:
        addrs: list[str] = []
        if hasattr(info, "ip_addresses") and info.ip_addresses:
            addrs = [str(a) for a in info.ip_addresses]
        elif hasattr(info, "addresses") and info.addresses:
            addrs = [str(a) for a in info.addresses]
        
        if addrs:
            # Same precedence as the dict branch above, which is the one the
            # tests exercised -- this is the branch a real ZeroconfServiceInfo
            # takes, so it was still handing a 169.254 address to _probe_tcp.
            host = (
                next((a for a in addrs if _is_routable_v4(a)), None)
                or next((a for a in addrs if ":" not in a), None)
                or addrs[0]
            )
        elif getattr(info, "host", None):
            host = str(info.host)
        elif getattr(info, "hostname", None):
            host = str(info.hostname).rstrip(".")
            
        # Extract MAC from properties. Home Assistant hands these over decoded
        # (`decoded_properties`: str keys and values); looking them up by bytes
        # keys, as this used to, never matched, so no MAC was ever stored.
        # Bytes are still accepted for anything that passes raw TXT records.
        if hasattr(info, "properties") and info.properties:
            props = info.properties
            for k in ("mac", "device_mac", "serial"):
                val = props.get(k)
                if val is None:
                    val = props.get(k.encode())
                if isinstance(val, (bytes, bytearray)):
                    try:
                        val = val.decode("utf-8")
                    except UnicodeDecodeError:
                        val = None
                if val:
                    mac = str(val).upper()
                    break
        
    except Exception:
        pass
        
    return (host, mac)

def detect_camera_type(data: Mapping[str, Any] | None, previous: str | None = None) -> str | None:
    """The camera a printer serves: "webrtc", "mjpeg" or "mjpeg_optional".

    Decided from evidence and never from the model alone. Firmware 1.3.5.22
    moved the K1C and K1 Max from mjpg-streamer on :8080 to WebRTC on :8000 and
    announces it with `webrtcSupport: 1`; nothing on :8080 answers any more, so
    a K1C taken for MJPEG shows no video at all (#46). The K2 family is WebRTC
    whatever it reports.

    `previous` is the type already in use. A missing `webrtcSupport` key keeps
    it: frames arrive piecemeal, and deciding on a frame that has the model but
    not yet the flag would flip a working WebRTC camera back to MJPEG. Without
    telemetry at all, nothing is known and `previous` is returned too.
    """
    d = data or {}
    if not (d.get("model") or d.get("modelVersion")):
        return previous
    detected = ModelDetection(d)
    if detected.is_k2_family or d.get("webrtcSupport") == 1:
        # A printer go2rtc got no video from stays on direct WebRTC (#46).
        return "webrtc_direct" if previous == "webrtc_direct" else "webrtc"
    if "webrtcSupport" in d or previous is None:
        return "mjpeg_optional" if (detected.is_k1_se or detected.is_ender_v3_family) else "mjpeg"
    return previous


# The first version whose Auto camera needs a lasting silence before it moves to
# direct WebRTC (#134); a verdict cached by an older one is retried once.
DIRECT_FALLBACK_RULE_VERSION = (0, 9, 10)


def camera_type_to_keep(previous: str | None, cached_version: Any) -> str | None:
    """The cached camera type to carry into re-detection after an upgrade.

    A `webrtc_direct` verdict reached before 0.9.10 took two silent go2rtc
    snapshots 20 s apart, which a booting printer also produces, and it is
    cached for good: a K1 Max go2rtc streams fine sat on direct WebRTC, blank
    outside the LAN (#134). Such a verdict is dropped once, so go2rtc is tried
    again under the rule that needs ten minutes of silence. Anything else, or a
    version that cannot be read as older, is kept.
    """
    if previous != "webrtc_direct":
        return previous
    try:
        parts = tuple(int(part) for part in str(cached_version).split(".")[:3])
    except ValueError:
        return previous
    return None if parts < DIRECT_FALLBACK_RULE_VERSION else previous


def normalize_printer_hostname(value: Any) -> str | None:
    """A printer hostname comparable between mDNS and telemetry, or None.

    mDNS announces `K1C-C627.local.`; the printer's own telemetry says
    `K1C-C627`. Both reduce to `k1c-c627`.
    """
    if not isinstance(value, str):
        return None
    name = value.strip().rstrip(".").lower()
    if name.endswith(".local"):
        name = name[: -len(".local")]
    return name or None


# What setup caches as the model when the printer has not said (off at first
# setup, or `model` late). Not a model: never let it decide one.
PLACEHOLDER_MODEL = "K by Creality"


class ModelDetection:
    """Detect printer model and capabilities from telemetry data.

    Looks at both "model" (friendly) and "modelVersion" (board code like F012).
    Provides capability flags and a resolved model name if possible.
    """
    
    # Klipper output_pin name per model for LED brightness (SET_PIN dimming).
    # Keys are ModelDetection boolean-attribute names (evaluated in order); the
    # value is the Klipper output_pin name. Extend this to enable dimming for
    # more models.
    LED_PIN_BY_MODEL: ClassVar[dict[str, str]] = {
        "is_k2_base": "LED",
        "is_k2_pro": "LED",
        "is_k2_plus": "LED",
    }

    def __init__(self, coord_data):
        d = coord_data or {}
        self.model = d.get("model") or ""
        self.model_l = str(self.model).lower()
        self.model_version = d.get("modelVersion") or ""
        self.model_ver_u = str(self.model_version).upper()
        
        # Check for explicit WebRTC support flag (present in 2025 models)
        self.supports_webrtc = bool(d.get("webrtcSupport") == 1)
        
        # Individual printer model detection
        # Detect specific K1 variants first so the base detector can exclude them
        # K1 SE - "K1 SE"
        self.is_k1_se = "k1 se" in self.model_l

        # K1 Max - "CR-K1 Max"
        self.is_k1_max = "cr-k1 max" in self.model_l

        # K1C - "K1C"
        self.is_k1c = "k1c" in self.model_l

        # K1 Base - "CR-K1" or an exact "k1" model. Exclude SE/C/Max variants.
        # Avoid matching substrings that would incorrectly mark variants as base.
        self.is_k1_base = (
            ("cr-k1" in self.model_l or self.model_l.strip() == "k1")
            and not (self.is_k1_se or self.is_k1_max or self.is_k1c)
        )
        
        # K2 Base/Pro/Plus via board codes (appear in modelVersion)
        self.is_k2_base = ("F021" in self.model) or ("F021" in self.model_ver_u)
        self.is_k2_pro = ("F012" in self.model) or ("F012" in self.model_ver_u)
        self.is_k2_plus = ("F008" in self.model) or ("F008" in self.model_ver_u)
        
        # Ender-3 V3 KE - "F005"
        self.is_ender_v3_ke = (
            ("F005" in self.model) or ("F005" in self.model_ver_u) or
            ("ender-3 v3 ke" in self.model_l)
        )
        
        # Ender-3 V3 Plus - "F002"
        self.is_ender_v3_plus = (
            ("F002" in self.model) or ("F002" in self.model_ver_u) or
            ("ender-3 v3 plus" in self.model_l)
        )
        
        # Ender-3 V3 - "F001"
        # Must be exactly "ender-3 v3" (not KE, Plus, or SE)
        # Check that it's not one of the variants first
        is_not_variant = not (
            self.is_ender_v3_ke or 
            self.is_ender_v3_plus
        )
        self.is_ender_v3 = (
            is_not_variant and (
                ("F001" in self.model) or ("F001" in self.model_ver_u) or
                ("ender-3 v3" in self.model_l)
            )
        )
        
        # Creality Hi - "F018"
        # "hi" as a word: as a substring it matched any model name that
        # happened to contain those two letters (R66).
        self.is_creality_hi = (
            ("F018" in self.model) or ("F018" in self.model_ver_u) or
            bool(re.search(r"\bhi\b", self.model_l))
        )
        
        # Family groupings
        # K1 Family
        self.is_k1_family = (
            self.is_k1_base or
            self.is_k1_se or
            self.is_k1_max or
            self.is_k1c or
            "k1" in self.model_l
        )
        
        # K2 Family
        self.is_k2_family = (
            self.is_k2_base or
            self.is_k2_pro or
            self.is_k2_plus or
            "k2" in self.model_l
        )
        
        # Ender-3 V3 Family
        self.is_ender_v3_family = (
            self.is_ender_v3_ke or
            self.is_ender_v3_plus or
            self.is_ender_v3 or
            ("ender" in self.model_l and "v3" in self.model_l)
        )
        
        # Feature detection
        # Chamber temperature control is only available on K2 family (Base/Pro/Plus)
        self.has_chamber_control = self.is_k2_family
        # Back-compat alias
        self.has_box_control = self.has_chamber_control

        # Chamber temperature sensor is present on K1 family (except K1 SE) and K2 family.
        # Not present on Ender V3 family, K1 SE, or Creality Hi.
        self.has_chamber_sensor = (
            (self.is_k1_base or self.is_k1c or self.is_k1_max) or self.is_k2_family
        ) and not self.is_ender_v3_family and not self.is_k1_se
        # Back-compat alias
        self.has_box_sensor = self.has_chamber_sensor

        # Light is present on most models except K1 SE and Ender V3 family
        self.has_light = not (self.is_k1_se or self.is_ender_v3_family)

        self.led_pin: str | None = next(
            (pin for attr, pin in self.LED_PIN_BY_MODEL.items() if getattr(self, attr, False)),
            None,
        )
        self.has_brightness_control = self.led_pin is not None

    # ---- Resolved/canonical model name helpers ----
    def canonical_model(self) -> str | None:
        """Return a canonical model name if derivable from codes.

        When the friendly model is missing, use modelVersion codes.
        """
        # K2 family by codes
        if self.is_k2_pro:
            return "K2 Pro"
        if self.is_k2_plus:
            return "K2 Plus"
        if self.is_k2_base:
            return "K2"
        # Ender 3 V3 family by codes
        if self.is_ender_v3_ke:
            return "Ender 3 V3 KE"
        if self.is_ender_v3_plus:
            return "Ender 3 V3 Plus"
        if self.is_ender_v3:
            return "Ender 3 V3"
        # Creality Hi
        if self.is_creality_hi:
            return "Creality Hi"
        return None

    def resolved_model(self) -> str:
        """Best-effort model string for device_info caching/UI.

        Prefer the printer-provided friendly "model", falling back to canonical
        mapping from codes, and lastly a generic label.
        """
        if self.model:
            return str(self.model)
        can = self.canonical_model()
        if can:
            return can
        return PLACEHOLDER_MODEL

    @classmethod
    def from_cache(cls, entry_data: Mapping[str, Any], live: Mapping[str, Any] | None = None) -> "ModelDetection":
        """Detection from the model cached in an entry, or live telemetry when
        nothing is cached yet."""
        live = live or {}
        cached = entry_data.get("_cached_model")
        if cached == PLACEHOLDER_MODEL:
            cached = None  # the printer had not said; the live model decides
        return cls({
            "model": cached or live.get("model"),
            "modelVersion": entry_data.get("_cached_model_version") or live.get("modelVersion"),
        })

    def display_model(self) -> tuple[str, str | None]:
        """The model name and model id for the device page (R80).

        The K2s and the Ender 3 V3 KE report a board code as `model` ("F012"),
        which the device page showed as the model. The name now comes from the
        code, and the code is the model id. `resolved_model` stays as it is: the
        model sensor shows it, and automations may compare against it.
        """
        name = self.canonical_model()
        if name and self.model and self.model != name:
            return name, str(self.model)
        return self.resolved_model(), None


# ---------- CFS filament helpers ----------

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _normalize_color_token(token: str) -> str:
    """Normalise one colour token to ``#rrggbb``, or return it unchanged."""
    raw = token.strip()
    if not raw:
        return token
    body = raw[1:] if raw.startswith("#") else raw
    if not _HEX_RE.match(body):
        return token
    if len(body) == 3:
        # Expanded, not passed through: the docstring promises #rrggbb, and a
        # short form otherwise gave `build_spool_key` two different ids for the
        # same colour (#abc vs #aabbcc). It also kept the value unwritable --
        # `normalize_material_color` refuses a three-digit colour -- so a card
        # prefilling from `color_hex` could not save what it was shown.
        return "#" + "".join(ch * 2 for ch in body.lower())
    if len(body) >= 6:
        # Creality pads the colour with a leading character, so the *last* six
        # hex digits are the real RRGGBB value.
        return f"#{body[-6:].lower()}"
    return token


def normalize_color_hex(value: Any) -> Any:
    """Normalise a CFS filament colour to ``#rrggbb``.

    Creality RFID tags store the colour as seven hex characters -- one padding
    character followed by the real ``RRGGBB`` -- and the printer streams that
    verbatim (e.g. ``#0ffffff``). Reading the first six characters yields the
    wrong colour, so the last six are kept instead (issues #113, #117).

    Anything that is not a recognisable hex colour is returned untouched, so
    sentinels ("N/A"), named colours and unexpected formats survive intact.
    Comma/semicolon separated lists are normalised element-wise for spools that
    report more than one colour.
    """
    if not isinstance(value, str):
        return value
    for sep in (",", ";"):
        if sep in value:
            return sep.join(_normalize_color_token(part) for part in value.split(sep))
    return _normalize_color_token(value)


def format_filament_label(vendor: Any, name: Any, material_type: Any = None) -> str | None:
    """Build the human-readable filament label for a CFS slot.

    The printer often repeats the vendor inside the material name (vendor
    ``Generic`` with name ``Generic PLA``), which naively joining the two turned
    into "Generic Generic PLA" (issue #115). An absent vendor is left out rather
    than replaced with a guess.
    """
    vendor_txt = str(vendor).strip() if vendor not in (None, "") else ""
    name_txt = str(name).strip() if name not in (None, "") else ""
    if not name_txt:
        name_txt = str(material_type).strip() if material_type not in (None, "") else ""
    if not name_txt:
        # The vendor alone, or None, which reads as Home Assistant's own,
        # translated "Unknown"; this used to append the English word (R33).
        return vendor_txt or None
    if not vendor_txt:
        return name_txt
    if name_txt.casefold().startswith(vendor_txt.casefold()):
        return name_txt
    return f"{vendor_txt} {name_txt}"


def _spool_key_part(value: Any) -> str:
    text = str(value).strip() if value not in (None, "") else ""
    return text.replace(" ", "-").lower()


def build_spool_key(
    *,
    rfid: Any = None,
    vendor: Any = None,
    material_type: Any = None,
    name: Any = None,
    color: Any = None,
) -> str | None:
    """Derive a stable per-spool identifier for external trackers.

    The printer's ``rfid`` field is a material/filament id, so two spools of the
    same material and vendor share it even when their colours differ, which
    stops tools like spoolmansync from telling them apart (issue #117).
    Appending the normalised colour disambiguates those.

    This is a *derived* key, not a tag serial: the telemetry carries no per-tag
    serial, so two genuinely identical spools still produce the same key.
    """
    ident = _spool_key_part(rfid)
    if not ident:
        ident = "-".join(
            part
            for part in (
                _spool_key_part(vendor),
                _spool_key_part(name) or _spool_key_part(material_type),
            )
            if part
        )

    # A multi-colour spool reports several values ("#0ffa800,#0ff97e1"); join
    # them with '-' so the key stays a single flat token.
    normalized = normalize_color_hex(color)
    color_part = ""
    if isinstance(normalized, str):
        tokens = [
            token.strip().lstrip("#").lower()
            for token in re.split(r"[,;]", normalized)
            if token.strip().lstrip("#")
        ]
        if tokens and all(_HEX_RE.match(token) for token in tokens):
            color_part = "-".join(tokens)

    return "_".join(part for part in (ident, color_part) if part) or None


# --------------------------------------------------------------------------- #
# Print state
# --------------------------------------------------------------------------- #

# States in which the printer is doing something that must not be interrupted.
# The CFS card mirrors this set, and a test cross-checks the two so they cannot
# drift apart.
# Every state derive_print_state can return; test_printer_card_layout.py reads
# its returns and holds this, and the card's copy, to them. The print status
# sensor offers these as its options (R36).
PRINT_STATES = (
    "off",
    "unknown",
    "error",
    "self-testing",
    "completed",
    "paused",
    "stopped",
    "printing",
    "processing",
    "idle",
)
BUSY_PRINT_STATES = frozenset({"printing", "paused", "processing", "self-testing"})


# States in which a print exists and therefore has a G-code preview worth
# showing: everything busy, plus a finished job whose model is still on the bed.
PREVIEW_PRINT_STATES = frozenset(BUSY_PRINT_STATES | {"completed"})


def print_seconds_left(data: Mapping[str, Any]) -> float | None:
    """Seconds remaining in the current print, or None.

    The printer streams this as `printLeftTime`; `printTimeLeft` is only kept
    as a fallback because the notification code used to look for that name
    exclusively, which meant the minutes-to-end notification never fired.
    """
    for key in ("printLeftTime", "printTimeLeft"):
        value = safe_float(data.get(key))
        if value is not None:
            return value
    return None


def print_finishing(data: Mapping[str, Any]) -> bool:
    """A job the printer has rounded up to 100% but is still running.

    A K1C reports 100 with time still on the clock (86 s in the 2026-10-25
    capture), drops back to 99, and only then ends the job, with state 2 and no
    time left. Reading 100% as the end announced the completion early and
    flapped the status back to printing for the 99 (R81). Only an explicit
    "printing or paused, with time left" holds the end back: a printer that
    reports no estimate, or one that leaves state 1 at the end, still finishes
    on its 100.
    """
    if data.get("state") not in (1, 5):
        return False
    left = print_seconds_left(data)
    return left is not None and math.isfinite(left) and left > 0


def derive_print_state(
    data: dict[str, Any],
    *,
    power_off: bool = False,
    available: bool = True,
    paused_flag: bool = False,
) -> str:
    """Derive the printer's operational state from a telemetry snapshot.

    Extracted from ``PrintStatusSensor`` so that services can gate on the same
    notion of "busy" the user sees on the dashboard, instead of re-deriving it
    slightly differently. Keep this the only place the mapping lives.
    """
    # Highest priority: the power switch, then a lost WebSocket.
    if power_off:
        return "off"
    if not available:
        return "unknown"

    # Both fields are normalised rather than trusted. This runs on the WebSocket
    # frame path, so a printer that reports `err` as a bare code instead of a
    # mapping, or `withSelfTest` as a string, would raise here and take the whole
    # state update with it -- and every entity reads its state through this.
    err = data.get("err")
    errcode = safe_float(err.get("errcode", 0) if isinstance(err, Mapping) else err)
    if errcode is not None and errcode != 0:
        return "error"

    self_test = safe_float(data.get("withSelfTest"))
    if self_test is not None and 1 <= self_test <= 99:
        return "self-testing"

    state = data.get("state")
    filename = data.get("printFileName") or ""
    progress = safe_float(
        data.get("printProgress") if data.get("printProgress") is not None
        else data.get("dProgress")
    )
    # `safe_float` happily returns nan/inf, and `int()` raises ValueError on the
    # first and OverflowError on the second. Same frame path as the fields above,
    # so treat a non-finite reading as no reading at all.
    if progress is None or not math.isfinite(progress):
        progress = -1
    else:
        progress = int(progress)

    if filename:
        if progress >= 100 and not print_finishing(data):
            return "completed"
        if state == 5 or paused_flag:
            return "paused"
        if state == 4:
            return "stopped"
        if state == 1:
            return "printing"
        # 7 while a cancel finishes the move under way: the K1C kept probing for
        # 30 s, raised Z, then reported 4, and read "idle" meanwhile (R29).
        # Busy, not an end: from one capture 7 cannot be ruled out elsewhere in
        # a print, and calling it "stopped" would announce a stop that did not
        # happen. 9 is the K1C starting a job, for under a second before 1;
        # read as "idle" it made every start stopped -> idle -> printing, which
        # fires automations waiting for idle (R89). The live card does not
        # start on "processing", so it costs no extra push.
        if state in (0, 7, 9):
            return "processing"

    return "idle"


def derive_activity_state(
    data: dict[str, Any],
    *,
    power_off: bool = False,
    available: bool = True,
    paused_flag: bool = False,
) -> str:
    """``derive_print_state`` with a *stale* error collapsed back to the job.

    ``derive_print_state`` reports ``"error"`` for any non-zero ``err.errcode``,
    including a code the printer never clears. Callers that want to know what
    the job is *doing* -- a live notification card, or whether a G-code preview
    exists -- must not be pinned to "error" for an entire print by a code that
    is never reset.

    Re-derives with the error blanked rather than re-implementing the mapping,
    so there is still exactly one place the state table lives. Anything that
    should react to a *new* fault keys on the error code changing instead.
    """
    state = derive_print_state(
        data, power_off=power_off, available=available, paused_flag=paused_flag
    )
    if state != "error":
        return state
    return derive_print_state(
        dict(data, err={}),
        power_off=power_off,
        available=available,
        paused_flag=paused_flag,
    )


# --------------------------------------------------------------------------- #
# CFS material writes
# --------------------------------------------------------------------------- #

_MATERIAL_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


class MaterialValueError(ValueError):
    """A material field that cannot be written, named by its translation key.

    The service turns it into a translated ServiceValidationError (R33); the
    English text is only for logs and tests.
    """

    def __init__(self, key: str, **placeholders: Any) -> None:
        self.key = key
        self.placeholders = {name: str(value) for name, value in placeholders.items()}
        detail = ", ".join(f"{name}={value}" for name, value in self.placeholders.items())
        super().__init__(f"{key}: {detail}" if detail else key)


def build_modify_material_payload(
    *,
    box_id: int,
    slot_id: int,
    material_type: str,
    name: str | None = None,
    vendor: str | None = None,
    color: Any = None,
    min_temp: Any = None,
    max_temp: Any = None,
    pressure: Any = None,
    rfid: Any = None,
) -> dict[str, Any]:
    """Build the ``modifyMaterial`` payload the printer expects.

    Kept free of Home Assistant so it can be unit tested directly. Raises
    ``ValueError`` on input the printer would not accept, rather than coercing it
    into something that silently writes the wrong thing.

    Only keys the caller actually supplied are included: the printer merges the
    payload into the slot it already has, so emitting a default would overwrite a
    real value with a guess. ``rfid`` matters most here -- sending ``""`` wipes
    the tag association on an RFID spool.
    """
    payload: dict[str, Any] = {
        "boxId": int(box_id),
        "id": int(slot_id),
        "type": str(material_type).strip(),
    }
    if not payload["type"]:
        raise MaterialValueError("material_type_empty")

    for key, value in (("name", name), ("vendor", vendor)):
        if value is not None and str(value).strip():
            payload[key] = str(value).strip()

    if color is not None:
        payload["color"] = normalize_material_color(color)

    def _number(name: str, value: Any) -> float | None:
        """Parse an optional number, refusing input that is not one.

        safe_float returning None is indistinguishable from "not supplied", so
        min_temp="abc" used to be dropped and reported as a successful write. The
        service schema coerces these fields, but a direct caller would get a
        silent no-op.
        """
        if value is None:
            return None
        parsed = safe_float(value)
        if parsed is None:
            raise MaterialValueError("material_not_a_number", field=name, value=value)
        # nan compares False against everything, so the min/max ordering check
        # below cannot reject it, and json.dumps emits bare NaN/Infinity -- which
        # is not valid JSON and would reach the printer as a malformed payload.
        if not math.isfinite(parsed):
            raise MaterialValueError("material_not_a_number", field=name, value=value)
        return parsed

    low = _number("min_temp", min_temp)
    high = _number("max_temp", max_temp)
    if low is not None and high is not None and high < low:
        raise MaterialValueError("material_temp_order", high=f"{high:g}", low=f"{low:g}")
    if low is not None:
        payload["minTemp"] = low
    if high is not None:
        payload["maxTemp"] = high

    advance = _number("pressure", pressure)
    if advance is not None:
        if not 0.0 <= advance <= 1.0:
            raise MaterialValueError("material_pressure_range", value=f"{advance:g}")
        payload["pressure"] = advance

    # Pass an existing tag id straight through; never substitute a placeholder.
    if rfid is not None and str(rfid).strip():
        payload["rfid"] = str(rfid).strip()

    return payload


def normalize_material_color(value: Any) -> str:
    """Validate a colour for *writing* and return it as lowercase ``#rrggbb``.

    Deliberately stricter than :func:`normalize_color_hex`, which normalises
    whatever the printer happens to stream. A write has to be exact, so anything
    that is not a single six-digit hex colour is rejected -- including the
    comma-separated multi-colour form, which cannot be expressed as one value and
    would otherwise be silently flattened.
    """
    if isinstance(value, (list, tuple)):
        # Not the color_rgb selector's list: this field takes one hex string.
        raise MaterialValueError("material_colour_list")
    text = str(value).strip()
    if re.search(r"[,;]", text):
        raise MaterialValueError("material_colour_multi", value=text)
    if not _MATERIAL_COLOR_RE.match(text):
        raise MaterialValueError("material_colour_invalid", value=text)
    return f"#{text.lstrip('#').lower()}"


def core_version_supported(
    version: tuple[int, int] | None, minimum: tuple[int, int]
) -> bool:
    """Whether the running Home Assistant core is new enough.

    Compared as a tuple of ints, never as a string: "2026.10" sorts *before*
    "2026.7" lexicographically, so a string compare would reject exactly the
    newer cores it is supposed to allow.

    An unreadable version passes. Not being able to determine the version is our
    problem, and refusing to start over it would be worse than whatever we were
    trying to guard against.
    """
    if version is None:
        return True
    return version >= minimum
