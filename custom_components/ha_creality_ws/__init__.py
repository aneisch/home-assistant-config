from __future__ import annotations
import logging
import json
import os
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse
from typing import Callable, List, Optional, Any

from homeassistant.config_entries import ConfigEntry #type: ignore[import]
from homeassistant.core import HomeAssistant, ServiceCall #type: ignore[import]
from homeassistant.exceptions import ConfigEntryNotReady #type: ignore[import]
from homeassistant.helpers.event import ( #type: ignore[import]
    async_track_time_interval,
    async_track_state_change_event,
)
import voluptuous as vol #type: ignore[import]

from .const import (
    DOMAIN, 
    STALE_AFTER_SECS, 
    CONF_POWER_SWITCH,
    CONF_GO2RTC_URL,
    CONF_GO2RTC_PORT,
    DEFAULT_GO2RTC_URL,
    DEFAULT_GO2RTC_PORT,
)
from .coordinator import KCoordinator
from .frontend import CrealityCardRegistration
from .utils import ModelDetection
from homeassistant.helpers import entity_registry as er  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "switch", "camera", "button", "number", "fan", "light", "image"]

# Import integration version from manifest

async def _get_integration_version(hass: HomeAssistant) -> str:
    """Get current integration version from manifest.json"""
    try:
        manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
        # Use Home Assistant's async file operations
        content = await hass.async_add_executor_job(
            lambda: open(manifest_path, "r").read()
        )
        manifest = json.loads(content)
        return manifest.get("version", "0.0.0")
    except Exception:
        return "0.0.0"

def _migrate_go2rtc_settings(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate go2rtc settings to entry options if not already set."""
    current_options = dict(entry.options)
    needs_update = False
    
    # Migrate go2rtc_url if missing or in data
    if not current_options.get(CONF_GO2RTC_URL):
        # Check if it was stored in entry.data (old location)
        old_url = entry.data.get(CONF_GO2RTC_URL)
        if old_url:
            current_options[CONF_GO2RTC_URL] = old_url
            needs_update = True
            _LOGGER.info("Migrated go2rtc_url from entry.data to options")
        else:
            # Set default if missing
            current_options[CONF_GO2RTC_URL] = DEFAULT_GO2RTC_URL
            needs_update = True
            _LOGGER.debug("Setting default go2rtc_url: %s", DEFAULT_GO2RTC_URL)
    
    # Migrate go2rtc_port if missing or in data
    if not current_options.get(CONF_GO2RTC_PORT):
        # Check if it was stored in entry.data (old location)
        old_port = entry.data.get(CONF_GO2RTC_PORT)
        if old_port:
            try:
                current_options[CONF_GO2RTC_PORT] = int(old_port)
            except (ValueError, TypeError):
                current_options[CONF_GO2RTC_PORT] = DEFAULT_GO2RTC_PORT
            needs_update = True
            _LOGGER.info("Migrated go2rtc_port from entry.data to options")
        else:
            # Set default if missing
            current_options[CONF_GO2RTC_PORT] = DEFAULT_GO2RTC_PORT
            needs_update = True
            _LOGGER.debug("Setting default go2rtc_port: %s", DEFAULT_GO2RTC_PORT)
    
    if needs_update:
        hass.config_entries.async_update_entry(entry, options=current_options)
        _LOGGER.info("Migrated go2rtc settings to entry options")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Creality integration from a config entry."""
    host: str = entry.data["host"]
    power_switch = entry.options.get(CONF_POWER_SWITCH)
    coord = KCoordinator(hass, host=host, power_switch=power_switch)

    try:
        await coord.async_start()
        # If printer is OFF, we intentionally don't wait for connectivity.
        if not coord.power_is_off():
            ok = await coord.wait_first_connect(timeout=8.0)
            if not ok:
                _LOGGER.warning("Initial connect not confirmed; will retry in background")
    except Exception as exc:
        await coord.async_stop()
        raise ConfigEntryNotReady(str(exc)) from exc

    # Get current integration version
    current_version = await _get_integration_version(hass)
    cached_version = entry.data.get("_cached_version", "0.0.0")
    
    # Detect and store device info during initial setup or on version upgrade
    # This is stored in entry.data which persists across restarts
    should_re_cache = (
        not entry.data.get("_device_info_cached") or
        cached_version != current_version
    )
    
    # Also re-cache if max temperature values are missing (migration from older versions)
    should_re_cache = should_re_cache or (
        entry.data.get("_cached_max_bed_temp") is None or
        entry.data.get("_cached_max_nozzle_temp") is None
    )
    
    if should_re_cache:
        _LOGGER.info(
            "Caching device info for %s (cached_version=%s, current_version=%s)",
            host, cached_version, current_version
        )
        # Wait a bit longer to ensure we get model info
        if not coord.power_is_off():
            ok = await coord.wait_first_connect(timeout=10.0)
            # After first connect, wait briefly for model fields to appear to reduce flakiness
            if ok:
                got_fields = await coord.wait_for_fields(["model", "modelVersion", "hostname"], timeout=6.0)
            else:
                got_fields = False
            if (ok and coord.data) or got_fields:
                # Store device info in entry data
                d = coord.data or {}
                printermodel = ModelDetection(d)
                model = printermodel.resolved_model() or entry.data.get("_cached_model") or "K by Creality"
                hostname = d.get("hostname") or entry.data.get("_cached_hostname")
                model_version = d.get("modelVersion") or entry.data.get("_cached_model_version")
                
                new_data = dict(entry.data)
                new_data["_device_info_cached"] = True
                new_data["_cached_version"] = current_version
                new_data["_cached_model"] = model
                new_data["_cached_hostname"] = hostname
                new_data["_cached_model_version"] = model_version
                new_data["_cached_has_light"] = printermodel.has_light
                # Prefer chamber_* keys; mirror to legacy box_* for back-compat
                new_data["_cached_has_chamber_sensor"] = printermodel.has_chamber_sensor
                new_data["_cached_has_chamber_control"] = printermodel.has_chamber_control
                new_data["_cached_has_box_sensor"] = printermodel.has_box_sensor
                new_data["_cached_has_box_control"] = printermodel.has_box_control
                # Heuristic promotions: if telemetry already exposes fields, promote capabilities
                if any(k in d for k in ("boxTemp", "targetBoxTemp", "maxBoxTemp")):
                    new_data["_cached_has_chamber_sensor"] = True
                    new_data["_cached_has_box_sensor"] = True  # legacy mirror
                if "lightSw" in d:
                    new_data["_cached_has_light"] = True
                
                # Cache max temperature values for temperature control limits
                new_data["_cached_max_bed_temp"] = d.get("maxBedTemp", entry.data.get("_cached_max_bed_temp"))
                new_data["_cached_max_nozzle_temp"] = d.get("maxNozzleTemp", entry.data.get("_cached_max_nozzle_temp"))
                # Cache chamber max; mirror to legacy box for back-compat
                new_data["_cached_max_chamber_temp"] = d.get("maxBoxTemp", entry.data.get("_cached_max_chamber_temp"))
                new_data["_cached_max_box_temp"] = new_data["_cached_max_chamber_temp"]
                
                # Re-detect camera type only if missing (not on every update)
                cached_camera_type = entry.data.get("_cached_camera_type")
                if not cached_camera_type:
                    new_data["_cached_camera_type"] = "webrtc" if printermodel.is_k2_family else (
                        "mjpeg_optional" if (printermodel.is_k1_se or printermodel.is_ender_v3_family) else "mjpeg"
                    )
                    _LOGGER.info("Camera type detected: %s", new_data["_cached_camera_type"])
                else:
                    # Keep existing camera type (don't override on updates)
                    new_data["_cached_camera_type"] = cached_camera_type
                
                hass.config_entries.async_update_entry(entry, data=new_data)
                _LOGGER.info(
                    "Device info cached: model=%s, camera=%s, version=%s",
                    model, new_data.get("_cached_camera_type"), current_version
                )
                
                # Migrate go2rtc settings if needed
                _migrate_go2rtc_settings(hass, entry)
        else:
            # Printer is off - update version only, keep existing cached data if available
            _LOGGER.info(
                "Printer is off, updating version only (keeping existing cached data if available)"
            )
            new_data = dict(entry.data)
            new_data["_device_info_cached"] = True
            new_data["_cached_version"] = current_version
            
            # Only set defaults if this is first-time setup (no cached model exists)
            if not new_data.get("_cached_model"):
                new_data["_cached_model"] = "K by Creality"
                new_data["_cached_has_light"] = True
                new_data["_cached_has_chamber_sensor"] = False
                new_data["_cached_has_chamber_control"] = False
                # Legacy mirrors
                new_data["_cached_has_box_sensor"] = False
                new_data["_cached_has_box_control"] = False
                new_data["_cached_camera_type"] = "mjpeg"
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            
            # Migrate go2rtc settings even when printer is off
            _migrate_go2rtc_settings(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord
    
    # Store entry_id in coordinator for easy access
    coord._config_entry_id = entry.entry_id

    # Register the Lovelace card (non-fatal on failure)
    try:
        card_register = CrealityCardRegistration(hass)
        await card_register.async_register()
    except Exception as exc:
        _LOGGER.warning("Lovelace card registration skipped due to error: %s", exc)

    # Listener for options updates
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Periodic state checker
    def _interval_check(_now) -> None:
        coord.check_stale()
        hass.loop.call_soon_threadsafe(coord.async_update_listeners)
    
    cancel_interval = async_track_time_interval(
        hass, _interval_check, timedelta(seconds=max(5, STALE_AFTER_SECS // 3))
    )
    entry.async_on_unload(cancel_interval)

    # Watcher for power switch state changes
    def _watch_power_switch(entity_id: Optional[str]) -> Callable:
        if not entity_id:
            return lambda: None
        
        async def _state_cb(event) -> None:
            await coord.async_handle_power_change()

        return async_track_state_change_event(hass, [entity_id], _state_cb)

    cancel_power_watch = _watch_power_switch(power_switch)
    entry.async_on_unload(cancel_power_watch)

    # --- Remove legacy entities (migration) ---
    try:
        reg = er.async_get(hass)
        host = coord.client._host
        # Old unique_ids to remove
        legacy = [
            ("switch", f"{host}-light"),
            ("number", f"{host}-model_fan_pct"),
            ("number", f"{host}-case_fan_pct"),
            ("number", f"{host}-side_fan_pct"),
        ]
        for domain_name, unique in legacy:
            ent_id = reg.async_get_entity_id(domain_name, DOMAIN, unique)
            if ent_id:
                reg.async_remove(ent_id)
    except Exception as exc:
        _LOGGER.debug("Legacy entity cleanup skipped: %s", exc)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register diagnostic service (only once per integration)
    if not hasattr(hass.data[DOMAIN], '_diagnostic_service_registered'):
        await _register_diagnostic_service(hass)
        hass.data[DOMAIN]['_diagnostic_service_registered'] = True
    
    _LOGGER.info("ha_creality_ws: setup complete")
    return True


async def _register_diagnostic_service(hass: HomeAssistant) -> None:
    """Register diagnostic service - outputs all data to logs (no file storage)."""
    
    async def diagnostic_dump(call: ServiceCall) -> None:
        """Collect and log telemetry data for all printers."""
        try:
            # Get all coordinators (all printer instances)
            coordinators: List[tuple[str, KCoordinator]] = []
            for entry_id, coord in hass.data[DOMAIN].items():
                if isinstance(coord, KCoordinator):
                    coordinators.append((entry_id, coord))
            
            if not coordinators:
                _LOGGER.error("No Creality printers found to dump data from")
                return
            
            # Create diagnostic data structure
            diagnostic_data = {
                "timestamp": datetime.now().isoformat(),
                "home_assistant_version": getattr(hass.config, 'version', 'unknown'),
                "integration_version": await _get_integration_version(hass),
                # Static list of supported models and headline capabilities for quick reference
                "supported_models": {
                    "k1_family": [
                        {"model": "K1", "chamber_sensor": True, "chamber_control": False, "light": True, "camera": "mjpeg"},
                        {"model": "K1C", "chamber_sensor": True, "chamber_control": False, "light": True, "camera": "mjpeg"},
                        {"model": "K1 SE", "chamber_sensor": False, "chamber_control": False, "light": False, "camera": "mjpeg_optional"},
                        {"model": "K1 Max", "chamber_sensor": True, "chamber_control": False, "light": True, "camera": "mjpeg"}
                    ],
                    "k2_family": [
                        {"model": "K2", "chamber_sensor": True, "chamber_control": False, "light": True, "camera": "webrtc"},
                        {"model": "K2 Pro", "chamber_sensor": True, "chamber_control": True, "light": True, "camera": "webrtc"},
                        {"model": "K2 Plus", "chamber_sensor": True, "chamber_control": True, "light": True, "camera": "webrtc"}
                    ],
                    "ender_3_v3_family": [
                        {"model": "Ender 3 V3", "chamber_sensor": False, "chamber_control": False, "light": False, "camera": "mjpeg_optional"},
                        {"model": "Ender 3 V3 KE", "chamber_sensor": False, "chamber_control": False, "light": False, "camera": "mjpeg_optional"},
                        {"model": "Ender 3 V3 Plus", "chamber_sensor": False, "chamber_control": False, "light": False, "camera": "mjpeg_optional"}
                    ],
                    "other": [
                        {"model": "Creality Hi", "chamber_sensor": False, "chamber_control": False, "light": True, "camera": "mjpeg"}
                    ]
                },
                "printers": {}
            }
            
            for entry_id, coord in coordinators:
                # Collect config entry details for this coordinator (non-sensitive)
                cfg_entry = hass.config_entries.async_get_entry(entry_id)
                entry_meta: dict[str, Any] = {
                    "entry_id": entry_id,
                    "title": getattr(cfg_entry, "title", None),
                    "options": {
                        "power_switch": cfg_entry.options.get(CONF_POWER_SWITCH) if cfg_entry else None,
                        "go2rtc_url": cfg_entry.options.get(CONF_GO2RTC_URL) if cfg_entry else None,
                        "go2rtc_port": cfg_entry.options.get(CONF_GO2RTC_PORT) if cfg_entry else None,
                    } if cfg_entry else {},
                    "cached": {
                        "model": cfg_entry.data.get("_cached_model") if cfg_entry else None,
                        "hostname": cfg_entry.data.get("_cached_hostname") if cfg_entry else None,
                        "model_version": cfg_entry.data.get("_cached_model_version") if cfg_entry else None,
                        "camera_type": cfg_entry.data.get("_cached_camera_type") if cfg_entry else None,
                        "has_light": cfg_entry.data.get("_cached_has_light") if cfg_entry else None,
                        "has_chamber_sensor": cfg_entry.data.get("_cached_has_chamber_sensor", cfg_entry.data.get("_cached_has_box_sensor")) if cfg_entry else None,
                        "has_chamber_control": cfg_entry.data.get("_cached_has_chamber_control", cfg_entry.data.get("_cached_has_box_control")) if cfg_entry else None,
                        "max_bed_temp": cfg_entry.data.get("_cached_max_bed_temp") if cfg_entry else None,
                        "max_nozzle_temp": cfg_entry.data.get("_cached_max_nozzle_temp") if cfg_entry else None,
                        "max_chamber_temp": cfg_entry.data.get("_cached_max_chamber_temp", cfg_entry.data.get("_cached_max_box_temp")) if cfg_entry else None,
                    } if cfg_entry else {},
                }

                # WebSocket connection diagnostics
                client = coord.client
                ws_diag = {
                    "ws_url": client._url(),
                    "ws_connected": client._ws is not None,
                    "ws_ready": getattr(client._ws_ready, "is_set", lambda: False)(),
                    "connected_once": getattr(client._connected_once, "is_set", lambda: False)(),
                    "task_running": bool(client._task and not client._task.done()),
                    "last_rx_monotonic": client.last_rx_monotonic(),
                }

                # Attempt a minimal crawl of the printer web UI to collect resource URLs
                try:
                    host = coord.client._host
                    urls_cache = getattr(coord, "_http_urls_accessed", None)
                    if urls_cache is None:
                        urls_cache = set()
                        setattr(coord, "_http_urls_accessed", urls_cache)

                    session = async_get_clientsession(hass)
                    for scheme in ("https", "http"):
                        base = f"{scheme}://{host}/"
                        try:
                            # Record the base URL attempt
                            urls_cache.add(base)
                            # Allow self-signed certs on local printers
                            ssl_opt = False if scheme == "https" else None
                            async with session.get(base, timeout=5, ssl=ssl_opt) as resp:  # type: ignore[arg-type]
                                if resp.status == 200:
                                    txt = await resp.text(errors="ignore")
                                    # Extract href/src URLs (shallow)
                                    for m in re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", txt, re.IGNORECASE):
                                        absu = urljoin(base, m)
                                        pu = urlparse(absu)
                                        if pu.scheme in ("http", "https") and pu.hostname == host:
                                            urls_cache.add(absu)
                        except Exception:
                            # Ignore crawl failures; we still record base URL
                            pass
                except Exception:
                    _LOGGER.debug("Diagnostic URL crawl skipped due to error", exc_info=True)

                printer_data = {
                    "host": client._host,
                    "available": coord.available,
                    "power_is_off": coord.power_is_off(),
                    "power_switch_entity": getattr(coord, "_power_switch_entity", None),
                    "http_urls_accessed": sorted(list(getattr(coord, "_http_urls_accessed", set()))) if hasattr(coord, "_http_urls_accessed") else [],
                    "paused_flag": coord.paused_flag(),
                    "pending_pause": coord.pending_pause(),
                    "pending_resume": coord.pending_resume(),
                    "last_rx_time": client.last_rx_monotonic(),
                    "ws": ws_diag,
                    "config_entry": entry_meta,
                    "telemetry_data": coord.data.copy() if coord.data else {}
                }
                
                # Add model detection info
                printermodel = ModelDetection(coord.data)
                model = (coord.data or {}).get("model") or ""
                model_l = str(model).lower()
                printer_data["model_detection"] = {
                    "raw_model": model,
                    "model_lower": model_l,
                    "is_k1_family": printermodel.is_k1_family,
                    "is_k1_base": printermodel.is_k1_base,
                    "is_k1c": printermodel.is_k1c,
                    "is_k1_se": printermodel.is_k1_se,
                    "is_k1_max": printermodel.is_k1_max,
                    "is_k2_family": printermodel.is_k2_family,
                    "is_k2_base": printermodel.is_k2_base,
                    "is_k2_pro": printermodel.is_k2_pro,
                    "is_k2_plus": printermodel.is_k2_plus,
                    "is_ender_v3_family": printermodel.is_ender_v3_family,
                    "is_creality_hi": printermodel.is_creality_hi
                }
                
                # Add feature detection (matching sensor.py logic)
                printer_data["feature_detection"] = {
                    "has_light": printermodel.has_light,
                    "has_chamber_sensor": printermodel.has_chamber_sensor,
                    "has_chamber_control": printermodel.has_chamber_control,
                    "camera_type": "webrtc" if printermodel.is_k2_family else 
                                  "mjpeg_optional" if (printermodel.is_k1_se or printermodel.is_ender_v3_family) else 
                                  "mjpeg"
                }
                
                diagnostic_data["printers"][entry_id] = printer_data
            
            # Convert to JSON string for UI display
            json_output = json.dumps(diagnostic_data, indent=2, ensure_ascii=False)
            
            
            # Log the diagnostic data to make it visible in Home Assistant logs (using WARNING level for visibility)
            _LOGGER.warning("=== CREALITY DIAGNOSTIC DATA START ===\n%s\n=== CREALITY DIAGNOSTIC DATA END ===", json_output)
            
            # Create a persistent notification with summary
            from homeassistant.components.persistent_notification import async_create as pn_async_create
            # persistent_notification.async_create is a normal async function in HA, but guard by not awaiting
            # in case the imported alias returns a non-awaitable (defensive for older versions or stubs).
            pn_async_create(
                hass,
                title="Creality Diagnostic Data",
                message=f"Diagnostic data collected for {len(diagnostic_data['printers'])} printer(s). Data size: {len(json_output)} bytes. Check the logs for the full JSON data.",
                notification_id="creality_diagnostic_data"
            )
                
        except Exception as exc:
            _LOGGER.exception("Failed to create diagnostic dump: %s", exc)
            if hasattr(call, 'response'):
                call.response = {"error": str(exc)}
    
    # Register the service
    schema = vol.Schema({
        vol.Optional("include_sensitive_data", default=False): bool,
    })
    
    hass.services.async_register(
        DOMAIN, 
        "diagnostic_dump", 
        diagnostic_dump, 
        schema=schema
    )
    
    _LOGGER.info("Diagnostic service registered: ha_creality_ws.diagnostic_dump")


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coord: KCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coord.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # If this is the last instance of the integration, unregister the card
    if not hass.data[DOMAIN]:
        card_register = CrealityCardRegistration(hass)
        await card_register.async_unregister()

    return unload_ok


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device) -> bool:
    """Remove a device from the device registry when requested by the user.

    Returning True allows Home Assistant to remove the device and any associated
    entities for this config entry. We don't keep any external resources tied
    to the device (streams, files, etc.), so no extra cleanup is required here.
    """
    try:
        _LOGGER.info(
            "ha_creality_ws: request to remove device %s for entry %s",
            getattr(device, 'id', device),
            entry.entry_id,
        )

        # If this device has our identifier (DOMAIN, host), clear cached data
        # so that re-creating the device starts from a clean slate.
        host: str | None = None
        for ident in getattr(device, 'identifiers', set()):
            if isinstance(ident, tuple) and len(ident) == 2 and ident[0] == DOMAIN:
                host = ident[1]
                break

        if host:
            # Drop all cached_* fields from entry.data
            new_data = dict(entry.data)
            removed_keys = []
            for k in list(new_data.keys()):
                if k.startswith("_cached_") or k == "_device_info_cached":
                    removed_keys.append(k)
                    new_data.pop(k, None)
            if removed_keys:
                hass.config_entries.async_update_entry(entry, data=new_data)
                _LOGGER.info(
                    "ha_creality_ws: cleared cached data on device removal for host=%s: %s",
                    host,
                    ", ".join(sorted(removed_keys)),
                )
    except Exception:
        _LOGGER.exception("ha_creality_ws: cleanup during device removal failed")
    return True