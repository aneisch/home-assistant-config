from __future__ import annotations
import logging
import asyncio
import json
import os
import time
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse
from typing import Callable, List, Optional, Any



from homeassistant.config_entries import ConfigEntry, OperationNotAllowed # type: ignore[import]
from homeassistant.core import HomeAssistant, ServiceCall # type: ignore[import]
from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore[import]
from homeassistant.helpers.event import (  # type: ignore[import]
    async_track_time_interval,
    async_track_state_change_event,
)
from homeassistant.helpers.typing import ConfigType  # type: ignore[import]
from homeassistant.const import (  # type: ignore[import]
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
import voluptuous as vol  # type: ignore[import]
from homeassistant.helpers import config_validation as cv, entity_registry as er, device_registry as dr # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore[import]
from homeassistant.components.persistent_notification import async_create as pn_async_create # type: ignore[import]

from .const import (
    DOMAIN, 
    STALE_AFTER_SECS, 
    CONF_POWER_SWITCH,
    CONF_POWER_SWITCH_ENABLED,
    CONF_CAMERA_MODE,
    CONF_POLLING_RATE,
    CONF_NOTIFY_DEVICE,
    CONF_NOTIFY_COMPLETED,
    CONF_NOTIFY_ERROR,
    CONF_NOTIFY_MINUTES_TO_END,
    CONF_MINUTES_TO_END_VALUE,
    CONF_GO2RTC_URL,
    CONF_GO2RTC_PORT,
    DEFAULT_GO2RTC_URL,
    DEFAULT_GO2RTC_PORT,
)
from .coordinator import KCoordinator
from .frontend import CrealityCardRegistration
from .utils import ModelDetection




_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "switch", "camera", "button", "number", "fan", "light", "image"]

# Import integration version from manifest

async def _get_integration_version(hass: HomeAssistant) -> str:
    """Get current integration version from manifest.json"""
    try:
        manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
        # Use Home Assistant's async file operations
        content = await hass.async_add_executor_job(
            lambda: open(manifest_path, "r", encoding="utf-8").read()
        )

        manifest = json.loads(content)
        return manifest.get("version", "0.0.0")
    except Exception:
        return "0.0.0"

def _migrate_go2rtc_settings(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate go2rtc settings and power switch to entry options if not already set."""
    current_options = dict(entry.options)
    needs_update = False
    
    # Migrate power switch to new format with enabled flag (one-time migration)
    if CONF_POWER_SWITCH_ENABLED not in current_options:
        # Migration needed - check if user had a power switch configured
        power_switch = current_options.get(CONF_POWER_SWITCH)
        
        # Check if it's a valid entity (non-empty string with domain separator)
        if power_switch and isinstance(power_switch, str) and power_switch.strip() and "." in power_switch:
            # User had a power switch configured - enable it
            current_options[CONF_POWER_SWITCH_ENABLED] = True
            current_options[CONF_POWER_SWITCH] = power_switch.strip()
            needs_update = True
            _LOGGER.info("Migrated power switch: enabled for existing entity %s", power_switch.strip())
        else:
            # User didn't have a power switch configured (or it was invalid) - disable it
            current_options[CONF_POWER_SWITCH_ENABLED] = False
            current_options[CONF_POWER_SWITCH] = None
            needs_update = True
            _LOGGER.info("Migrated power switch: disabled (no entity was configured)")
    
    # Migrate go2rtc_url if missing or in data
    if not current_options.get(CONF_GO2RTC_URL):
        # Check if it was stored in entry.data (old location)
        old_url = entry.data.get(CONF_GO2RTC_URL)
        if old_url:
            current_options[CONF_GO2RTC_URL] = old_url
            needs_update = True
            _LOGGER.info("Migrated go2rtc_url from entry.data to options")
    
    # Clean up "bad defaults" introduced in 0.9.0
    # If users have localhost:11984 set as custom config, remove it to restore 0.8.0 behavior (auto-discovery)
    elif current_options.get(CONF_GO2RTC_URL) == DEFAULT_GO2RTC_URL:
        # Check port too
        current_port = current_options.get(CONF_GO2RTC_PORT)
        if current_port == DEFAULT_GO2RTC_PORT:
            _LOGGER.info("Cleaning up default go2rtc settings (restoring auto-discovery)")
            current_options.pop(CONF_GO2RTC_URL)
            current_options.pop(CONF_GO2RTC_PORT)
            needs_update = True

    # Migrate go2rtc_port if missing or in data
    if not current_options.get(CONF_GO2RTC_PORT):
        # Check if it was stored in entry.data (old location)
        old_port = entry.data.get(CONF_GO2RTC_PORT)
        if old_port:
            try:
                current_options[CONF_GO2RTC_PORT] = int(old_port)
            except (ValueError, TypeError):
                # Don't set default here anymore
                pass
            needs_update = True
            _LOGGER.info("Migrated go2rtc_port from entry.data to options")
    
    if needs_update:
        hass.config_entries.async_update_entry(entry, options=current_options)
        _LOGGER.info("Migration complete for entry options")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Creality integration from a config entry."""
    # Run migrations first
    _migrate_go2rtc_settings(hass, entry)
    
    host: str = entry.data["host"]
    
    # Handle power switch - only use if both enabled and entity is set
    power_switch_enabled = entry.options.get(CONF_POWER_SWITCH_ENABLED, False)
    power_switch = entry.options.get(CONF_POWER_SWITCH)
    effective_power_switch = power_switch if (power_switch_enabled and power_switch) else None
    
    _LOGGER.info("Power switch config: enabled=%s, entity=%s, effective=%s", 
                 power_switch_enabled, power_switch, effective_power_switch)
    
    coord = KCoordinator(hass, host=host, power_switch=effective_power_switch, config_entry_id=entry.entry_id)

    try:
        await coord.async_start()
        # If printer is OFF, we intentionally don't wait for connectivity.
        if not coord.power_is_off():
            # Initial grace period is ~5 retries (~15-20s). Wait enough to cover it.
            ok = await coord.wait_first_connect(timeout=15.0)
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
        cached_version != current_version or
        entry.data.get("_last_ip") != host
    )
    
    # Store current IP to detect network changes later
    if entry.data.get("_last_ip") != host:
        new_data = dict(entry.data)
        new_data["_last_ip"] = host
        hass.config_entries.async_update_entry(entry, data=new_data)
        
    # Attempt to cache MAC address if not present
    if not entry.data.get("_cached_mac") and not coord.power_is_off():
        # In a real scenario, we might query M115 or check network info from the printer
        # For now, we will rely on upcoming zeroconf updates to populate this if the printer exposes it.
        # OR: If the coordinator captured it from initial handshake/data?
        # Creality printers are notoriously shy about their MAC in the JSON payload.
        pass
         
    # Also re-cache if max temperature values are missing (migration from older versions)
    should_re_cache = should_re_cache or (
        entry.data.get("_cached_max_bed_temp") is None or
        entry.data.get("_cached_max_nozzle_temp") is None
    )
    
    # Re-cache if CFS info is missing but cfsConnect is 1
    if not should_re_cache and coord.data.get("cfsConnect") == 1 and not entry.data.get("_cached_cfs_detected"):
        should_re_cache = True

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
                # Wait for basic fields to confirm model and capabilities
                await coord.wait_for_fields(["model", "modelVersion", "hostname"], timeout=6.0)
                
                # CFS / Telemetry Wait Sequence
                # If CFS detected, we MUST wait for boxsInfo to populate or sensors won't get created.
                if coord.data.get("cfsConnect") == 1:
                    _LOGGER.info("CFS connected; requesting box info and waiting...")
                    # Request updated info to be sure
                    await coord.client.request_boxs_info()
                    # Wait for it to arrive
                    await coord.wait_for_fields(["boxsInfo"], timeout=5.0)
                
                # Opportunistic wait for chamber/feature fields if not yet present
                # This helps the logic below verify capabilities
                if "maxBoxTemp" not in coord.data:
                    # Give a tiny storage for these lazier fields to arrive
                    await coord.wait_for_fields(["maxBoxTemp", "targetBoxTemp"], timeout=2.0)
            else:
                got_fields = False
            
            # Always update cache if we have data, even if wait timed out partially
            if (ok and coord.data):
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
                # Feature Promotion: Trust telemetry over model defaults
                # If printer reports chamber targets/temps, ENABLE capabilities
                if "targetBoxTemp" in d:
                    new_data["_cached_has_chamber_control"] = True
                    new_data["_cached_has_box_control"] = True
                if "boxTemp" in d or "maxBoxTemp" in d:
                    new_data["_cached_has_chamber_sensor"] = True
                    new_data["_cached_has_box_sensor"] = True
                if "lightSw" in d:
                    new_data["_cached_has_light"] = True
                
                # Cache CFS status
                new_data["_cached_cfs_detected"] = d.get("cfsConnect") == 1
                
                # Cache max temperature values for temperature control limits
                new_data["_cached_max_bed_temp"] = d.get("maxBedTemp", entry.data.get("_cached_max_bed_temp"))
                new_data["_cached_max_nozzle_temp"] = d.get("maxNozzleTemp", entry.data.get("_cached_max_nozzle_temp"))
                # Cache chamber max; mirror to legacy box for back-compat
                new_data["_cached_max_chamber_temp"] = d.get("maxBoxTemp", entry.data.get("_cached_max_chamber_temp"))
                new_data["_cached_max_box_temp"] = new_data["_cached_max_chamber_temp"]
                
                # Re-detect camera type only if missing (not on every update)
                cached_camera_type = entry.data.get("_cached_camera_type")
                cached_camera_type = entry.data.get("_cached_camera_type")
                if not cached_camera_type:
                    new_data["_cached_camera_type"] = "webrtc" if (printermodel.is_k2_family or printermodel.supports_webrtc) else (
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
    coord._config_entry_id = entry.entry_id  # pylint: disable=protected-access



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
        # Do not force listener updates here; rely on coordinator's internal logic (throttled)
        # hass.loop.call_soon_threadsafe(coord.async_update_listeners)
    
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
        host = coord.client.host

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

    # Register custom services
    await _register_custom_services(hass)
    
    _LOGGER.info("ha_creality_ws: setup complete")
    return True


async def _register_custom_services(hass: HomeAssistant) -> None:
    """Register custom services for the integration."""

    async def request_cfs_info(call: ServiceCall) -> None:
        """Service to manually request CFS info from all or specific printers."""
        device_ids = call.data.get("device_id")
        target_entry_ids = set()
        
        # If devices selected, resolve them to config entries
        if device_ids:
            dev_reg = dr.async_get(hass)
            # Handle single string or list
            if isinstance(device_ids, str):
                device_ids = [device_ids]
                
            for dev_id in device_ids:
                device = dev_reg.async_get(dev_id)
                if device:
                    for entry_id in device.config_entries:
                        target_entry_ids.add(entry_id)
        
        # Collect coordinators to target
        targets = []
        for entry_id, coord in hass.data[DOMAIN].items():
            if isinstance(coord, KCoordinator):
                # If no devices selected, target all. Otherwise, check if entry matches.
                if not target_entry_ids or entry_id in target_entry_ids:
                    targets.append(coord)
        
        if not targets:
            _LOGGER.warning("No applicable printers found for CFS info request")
            return

        success_count = 0
        fail_count = 0
        
        for coord in targets:
            try:
                _LOGGER.info("Manually requesting CFS info for %s", coord.client.host)
                await coord.client.request_boxs_info()
                success_count += 1
            except Exception as exc:
                _LOGGER.error("Failed to request CFS info for %s: %s", coord.client.host, exc)
                fail_count += 1
        
        # Notify user of results
        pn_async_create(
            hass,
            title="CFS Info Request",
            message=f"Request sent to {success_count} printer(s).\nFailures: {fail_count}",
            notification_id="cfs_request_result"
        )

    if not hass.services.has_service(DOMAIN, "request_cfs_info"):
        hass.services.async_register(DOMAIN, "request_cfs_info", request_cfs_info)


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
                "printers": {}
            }

            
            for entry_id, coord in coordinators:
                # Collect config entry details for this coordinator (non-sensitive)
                cfg_entry = hass.config_entries.async_get_entry(entry_id)
                entry_meta: dict[str, Any] = {
                    "entry_id": entry_id,
                    "title": getattr(cfg_entry, "title", None),
                    "options": {
                        "power_switch": cfg_entry.options.get(CONF_POWER_SWITCH),
                        "power_switch_enabled": cfg_entry.options.get(CONF_POWER_SWITCH_ENABLED),
                        "camera_mode": cfg_entry.options.get(CONF_CAMERA_MODE),
                        "polling_rate": cfg_entry.options.get(CONF_POLLING_RATE),
                        "notify_device": cfg_entry.options.get(CONF_NOTIFY_DEVICE),
                        "notify_completed": cfg_entry.options.get(CONF_NOTIFY_COMPLETED),
                        "notify_error": cfg_entry.options.get(CONF_NOTIFY_ERROR),
                        "notify_minutes_to_end": cfg_entry.options.get(CONF_NOTIFY_MINUTES_TO_END),
                        "minutes_to_end_value": cfg_entry.options.get(CONF_MINUTES_TO_END_VALUE),
                        "go2rtc_url": cfg_entry.options.get(CONF_GO2RTC_URL),
                        "go2rtc_port": cfg_entry.options.get(CONF_GO2RTC_PORT),
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
                    "ws_url": client.get_url(),
                    "ws_connected": client.is_connected,
                    "ws_ready": client.is_connected,  # approximate mapping
                    "connected_once": client.has_connected_once(),
                    "task_running": client.is_task_running(),
                    "last_rx_monotonic": client.last_rx_monotonic(),
                    "reconnect_count": client.reconnect_count,
                    "msg_count": client.msg_count,
                    "last_error": client.last_error,
                    # Accessing private memeber for debug/diagnostics is acceptable or expose another property?
                    # uptime_start is public in ws_client (lines 66)
                    "uptime_seconds": (time.monotonic() - client.uptime_start) if client.uptime_start > 0 and client.is_connected else 0,
                }

                # Attempt a minimal crawl of the printer web UI to collect resource URLs
                try:
                    host = coord.client.host

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
                    "host": client.host,

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
                    "is_creality_hi": printermodel.is_creality_hi,
                    "supports_webrtc": printermodel.supports_webrtc
                }
                
                # Add feature detection (matching sensor.py logic)
                printer_data["feature_detection"] = {
                    "has_light": printermodel.has_light,
                    "has_chamber_sensor": printermodel.has_chamber_sensor,
                    "has_chamber_control": printermodel.has_chamber_control,
                    "camera_type": "webrtc" if (printermodel.is_k2_family or printermodel.supports_webrtc) else 
                                  "mjpeg_optional" if (printermodel.is_k1_se or printermodel.is_ender_v3_family) else 
                                  "mjpeg"
                }

                # CFS Diagnostics
                cfs_data = coord.data.get("boxsInfo", {})
                cfs_status = {
                    "connected": coord.data.get("cfsConnect"),
                    "box_count": len(cfs_data.get("materialBoxs", [])),
                    "raw_boxsInfo": cfs_data,
                }
                printer_data["cfs"] = cfs_status


                # Dump actual HA entities
                ent_reg = er.async_get(hass)
                # er.async_entries_for_config_entry returns list of RegistryEntry
                entity_entries = er.async_entries_for_config_entry(ent_reg, entry_id)
                entities_dump = []
                for e in entity_entries:
                    st = hass.states.get(e.entity_id)
                    entities_dump.append({
                        "entity_id": e.entity_id,
                        "name": e.name or e.original_name,
                        "state": st.state if st else None,
                        "attributes": dict(st.attributes) if st else None
                    })
                printer_data["entities"] = entities_dump
                
                diagnostic_data["printers"][entry_id] = printer_data
            
            # Convert to JSON string for UI display
            json_output = json.dumps(diagnostic_data, indent=2, ensure_ascii=False)
            
            
            # Log the diagnostic data to make it visible in Home Assistant logs (using WARNING level for visibility)
            _LOGGER.warning("=== CREALITY DIAGNOSTIC DATA START ===\n%s\n=== CREALITY DIAGNOSTIC DATA END ===", json_output)
            
            # Create a persistent notification with summary
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

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_monitor_zeroconf_update(hass: HomeAssistant, entry: ConfigEntry, info: Any) -> None:
    """Handle triggered Zeroconf update."""
    from .utils import extract_info_from_zeroconf
    host, mac = extract_info_from_zeroconf(info)
    
    if not host:
        return

    # If we have a MAC address, we can do a robust match
    if mac:
        # Check if the current entry matches this MAC
        cached_mac = entry.data.get("_cached_mac")
        
        # Scenario 1: We already know our MAC and it matches the discovery
        if cached_mac and cached_mac.upper() == mac.upper():
            current_host = entry.data.get("host")
            if host != current_host:
                _LOGGER.warning(
                    "Robust IP Update: MAC match (%s) but IP changed from %s to %s. Updating...",
                    mac, current_host, host
                )
                hass.config_entries.async_update_entry(entry, data={**entry.data, "host": host, "_last_ip": host})
                await hass.config_entries.async_reload(entry.entry_id)
            return

        # Scenario 2: We don't know our MAC yet, but this update is targeting *us* by IP (initial discovery phase?)
        # Or more likely, HA matched the zeroconf flow to this entry for some reason.
        # If we don't have a cached MAC, and the IP matches, let's CACHE this MAC!
        current_host = entry.data.get("host")
        if host == current_host and not cached_mac:
            _LOGGER.info("Caching MAC address found via Zeroconf: %s", mac)
            hass.config_entries.async_update_entry(entry, data={**entry.data, "_cached_mac": mac})
            return

    # Fallback to simple name/IP matching logic or legacy checks
    # If users rely on hostname, IP-based recovery without MAC is dangerous (DHCP shuffle).



async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - force full reload to apply power switch changes."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            _LOGGER.info("Reloading entry due to options update (attempt %d/%d)", attempt + 1, max_retries)
            await hass.config_entries.async_reload(entry.entry_id)
            _LOGGER.info("Entry reloaded successfully")
            return
        except OperationNotAllowed as exc:
            if attempt < max_retries - 1:
                _LOGGER.debug("Reload blocked (UNLOAD_IN_PROGRESS), retrying in 0.5s...")
                await asyncio.sleep(0.5)
            else:
                _LOGGER.warning("Reload failed after %d attempts: %s", max_retries, exc)
        except Exception as exc:
            _LOGGER.error("Unexpected error during reload: %s", exc)
            return


async def _retry_reload_later(hass: HomeAssistant, entry: ConfigEntry) -> None:
    try:
        await asyncio.sleep(1.0)
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception:
        pass


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
