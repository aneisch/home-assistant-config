"""Diagnostics for Creality printers: the standard download, and the dump service.

One builder serves both. Settings > Devices & services > the printer > "Download
diagnostics" is Home Assistant's own path and always redacted; the
`diagnostic_dump` action returns the same data as its response, redacted unless
`include_sensitive_data` is set.

Before this, the action only wrote the data to the log at WARNING, unredacted
(entity attributes carried the camera's access token), while the README, the
bug form and the issue bot all told reporters to copy it from a response that
did not exist.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, is_dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from homeassistant.components.diagnostics import REDACTED, async_redact_data  # type: ignore[import]
from homeassistant.config_entries import ConfigEntry  # type: ignore[import]
from homeassistant.const import __version__ as HA_VERSION  # type: ignore[import]
from homeassistant.core import HomeAssistant  # type: ignore[import]
from homeassistant.helpers import entity_registry as er  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]
from homeassistant.util import dt as dt_util  # type: ignore[import]

from .const import DOMAIN
from .utils import ModelDetection, detect_camera_type

# Addresses, the printer's own name (it embeds part of its MAC), people's phone
# names in notify targets, and anything carrying an access token.
TO_REDACT = {
    "host",
    "hostname",
    "_cached_hostname",
    "_cached_mac",
    "_last_ip",
    "mac",
    "ws_url",
    "title",
    "unique_id",
    "access_token",
    "entity_picture",
    "notify_device",
    "notify_targets",
    "targets",
    "http_urls_accessed",
    "web_ui_urls",
    "configuration_url",
    "go2rtc_url",
    # Custom mode takes rtsp://user:password@host/...; the host is usually an
    # NVR or a camera, which the address scrub below never sees.
    "custom_camera_url",
    # Entity attributes: the device is named after the printer's hostname, and
    # the camera and preview attributes carry its address.
    "friendly_name",
    "upstream_signaling_url",
    "stream_source",
    "source_url",
    "go2rtc_stream_name",
}


def _jsonable(value: Any) -> Any:
    """What a service response and the download can both carry."""
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _scrub(value: Any, needles: list[str]) -> Any:
    """Replace each needle inside every string, at any depth.

    Key-based redaction cannot reach an address embedded in free text, and the
    connection's `last_error` is exactly that: "Connect call failed
    ('192.168.0.90', 9999)". Dropping the message would lose what it says.
    """
    if isinstance(value, dict):
        return {k: _scrub(v, needles) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, needles) for v in value]
    if isinstance(value, str):
        for needle in needles:
            value = value.replace(needle, REDACTED)
        return value
    return value


def _identifying_strings(hass: HomeAssistant) -> list[str]:
    """Every printer address and network name this instance knows, longest first."""
    found: set[str] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        data = getattr(entry, "data", None) or {}
        for key in ("host", "_last_ip", "_cached_hostname", "_cached_mac"):
            text = str(data.get(key) or "").strip()
            if len(text) >= 4:
                found.add(text)
        # The device is named after the hostname, so entity ids carry it
        # slugified: "K1C-C627" is "k1c_c627" in sensor.k1c_c627_nozzle_temperature.
        slug = re.sub(r"[^a-z0-9]+", "_", str(data.get("_cached_hostname") or "").lower()).strip("_")
        if len(slug) >= 4:
            found.add(slug)
    return sorted(found, key=len, reverse=True)


def redact(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Key-based redaction, then the addresses and names wherever they appear."""
    return _scrub(async_redact_data(data, TO_REDACT), _identifying_strings(hass))


def printer_diagnostics(hass: HomeAssistant, entry: ConfigEntry, coord: Any) -> dict[str, Any]:
    """Everything known about one printer, unredacted."""
    data = coord.data or {}
    client = coord.client
    detected = ModelDetection(data)
    cache = {k: v for k, v in entry.data.items() if k.startswith("_cached_") or k == "_last_ip"}

    ent_reg = er.async_get(hass)
    entities = []
    for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        st = hass.states.get(reg.entity_id)
        entities.append({
            "entity_id": reg.entity_id,
            "unique_id": reg.unique_id,
            "disabled_by": reg.disabled_by,
            "state": st.state if st else None,
            "attributes": dict(st.attributes) if st else None,
        })

    live_card = getattr(coord, "_live_card", None)
    notifications = {
        "targets": list(getattr(coord, "_notify_targets", []) or []),
        # A list in target order, not a dict keyed by target: redaction works
        # on keys' values, so a target as a key would leak a person's phone name.
        "target_platforms": [
            dict(zip(("os_name", "manufacturer"), coord._target_platform(target)))
            for target in (getattr(coord, "_notify_targets", []) or [])
            if hasattr(coord, "_target_platform")
        ],
        "live_card_enabled": getattr(coord, "_notify_live", None),
        "actions_enabled": getattr(coord, "_notify_actions", None),
        "completed": getattr(coord, "_notify_completed", None),
        "error": getattr(coord, "_notify_error", None),
        # A slots dataclass: no __dict__, so _jsonable converts it.
        "live_card": live_card,
        "strings_loaded": getattr(coord, "_notify_strings", None) is not None,
    }

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
            "host": entry.data.get("host"),
            "options": dict(entry.options),
            "cache": cache,
        },
        "connection": {
            "ws_url": client.get_url(),
            "connected": client.is_connected,
            "connected_once": client.has_connected_once(),
            "task_running": client.is_task_running(),
            "available": coord.available,
            "power_is_off": coord.power_is_off(),
            "power_switch_entity": getattr(coord, "_power_switch_entity", None),
            "reconnect_count": client.reconnect_count,
            "msg_count": client.msg_count,
            "last_error": client.last_error,
            # Printer-local URLs the integration has fetched (preview image).
            "http_urls_accessed": sorted(getattr(coord, "_http_urls_accessed", set()) or []),
            "uptime_seconds": (
                time.monotonic() - client.uptime_start
                if client.uptime_start > 0 and client.is_connected
                else 0
            ),
        },
        "printer": {
            "paused_flag": coord.paused_flag(),
            "pending_pause": coord.pending_pause(),
            "pending_resume": coord.pending_resume(),
            "camera_type_in_use": getattr(coord, "camera_type_in_use", None),
            "camera_type_detected": detect_camera_type(data, cache.get("_cached_camera_type")),
            "model_detection": {
                name: getattr(detected, name)
                for name in (
                    "is_k1_family", "is_k1_base", "is_k1c", "is_k1_se", "is_k1_max",
                    "is_k2_family", "is_k2_base", "is_k2_pro", "is_k2_plus",
                    "is_ender_v3_family", "is_creality_hi", "supports_webrtc",
                    "has_light", "has_chamber_sensor", "has_chamber_control",
                )
            },
        },
        "notifications": notifications,
        "telemetry": dict(data),
        "entities": entities,
    }


async def async_crawl_web_ui(hass: HomeAssistant, host: str) -> list[str]:
    """Same-host URLs the printer's own web UI links to.

    Dump action only, never the download: it makes requests to the printer.
    Kept because it is how a new model's endpoints (a camera path, a preview
    path) have been found in reporters' dumps.
    """
    found: set[str] = set()
    session = async_get_clientsession(hass)
    for scheme in ("https", "http"):
        base = f"{scheme}://{host}/"
        found.add(base)
        try:
            # Printers serve a self-signed certificate, if any.
            ssl_opt = False if scheme == "https" else None
            async with session.get(base, timeout=5, ssl=ssl_opt) as resp:  # type: ignore[arg-type]
                if resp.status != 200:
                    continue
                text = await resp.text(errors="ignore")
        except Exception:  # pylint: disable=broad-except
            continue
        for ref in re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", text, re.IGNORECASE):
            url = urljoin(base, ref)
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.hostname == host:
                found.add(url)
    return sorted(found)


async def async_collect(hass: HomeAssistant, integration_version: str | None) -> dict[str, Any]:
    """All loaded printers, unredacted, for the dump action."""
    printers: dict[str, Any] = {}
    for entry_id, coord in (hass.data.get(DOMAIN) or {}).items():
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or not hasattr(coord, "client"):
            continue
        printer = printer_diagnostics(hass, entry, coord)
        printer["connection"]["web_ui_urls"] = await async_crawl_web_ui(hass, coord.client.host)
        printers[entry_id] = printer
    return _jsonable({
        "timestamp": dt_util.utcnow().isoformat(),
        "home_assistant_version": HA_VERSION,
        "integration_version": integration_version,
        "printers": printers,
    })


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Settings > Devices & services > Download diagnostics."""
    coord = (hass.data.get(DOMAIN) or {}).get(entry.entry_id)
    if coord is None:
        return redact(
            hass, _jsonable({"entry": {"options": dict(entry.options), "data": dict(entry.data)}})
        )
    return redact(hass, _jsonable(printer_diagnostics(hass, entry, coord)))
