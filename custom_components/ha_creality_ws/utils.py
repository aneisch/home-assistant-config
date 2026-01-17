from __future__ import annotations

import re
from typing import Any, Optional

__all__ = [
    "coerce_numbers",
    "parse_model_version",
    "parse_position",
    "safe_float",
    "extract_host_from_zeroconf",
]


def coerce_numbers(d: dict[str, Any]) -> dict[str, Any]:
    """Convert numeric strings in a dict to numbers where safe."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                out[k] = float(v) if "." in v else int(v)
                continue
            except Exception:
                pass
        out[k] = v
    return out


def parse_model_version(s: str | None) -> tuple[str | None, str | None]:
    """Extract HW/SW versions from a semi-structured string (Creality format)."""
    if not s or not isinstance(s, str):
        return (None, None)

    parts: dict[str, Optional[str]] = {}
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


def extract_host_from_zeroconf(info: Any) -> Optional[str]:
    """Compatibility wrapper for extract_info_from_zeroconf returning only host."""
    host, _ = extract_info_from_zeroconf(info)
    return host

def extract_info_from_zeroconf(info: Any) -> tuple[Optional[str], Optional[str]]:
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
                # Prefer IPv4 addresses when present (no ':' in string)
                v4 = next((a for a in addrs_raw if ":" not in str(a)), None)
                host = str(v4 or addrs_raw[0])
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
            v4 = next((a for a in addrs if ":" not in a), None)
            host = v4 or addrs[0]
        elif getattr(info, "host", None):
            host = str(info.host)
        elif getattr(info, "hostname", None):
            host = str(info.hostname).rstrip(".")
            
        # Extract MAC from properties
        if hasattr(info, "properties") and info.properties:
            # Check for MAC in properties
            # Note: HA zeroconf properties are usually bytes, needing decode
            props = info.properties
            for k in (b"mac", b"device_mac", b"serial"):
                val = props.get(k)
                if val:
                    try:
                        mac_str = val.decode("utf-8")
                        mac = mac_str.upper()
                        break
                    except Exception:
                        pass
        
    except Exception:
        pass
        
    return (host, mac)

class ModelDetection:
    """Detect printer model and capabilities from telemetry data.

    Looks at both "model" (friendly) and "modelVersion" (board code like F012).
    Provides capability flags and a resolved model name if possible.
    """
    
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
        self.is_creality_hi = (
            ("F018" in self.model) or ("F018" in self.model_ver_u) or
            ("hi" in self.model_l)
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
        return "K by Creality"