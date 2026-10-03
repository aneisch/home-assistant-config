from __future__ import annotations
import logging
import asyncio
import json
import os
import time
from datetime import timedelta
import re
from urllib.parse import urljoin, urlparse
from collections.abc import Callable
from typing import Any



from homeassistant.config_entries import ConfigEntry, OperationNotAllowed # type: ignore[import]
from homeassistant.core import HomeAssistant, ServiceCall, callback # type: ignore[import]
from homeassistant.const import __version__ as HA_VERSION  # type: ignore[import]
from homeassistant.util import dt as dt_util  # type: ignore[import]
from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore[import]
try:
    from homeassistant.exceptions import ConfigEntryError  # type: ignore[import]
    _CONFIG_ENTRY_ERROR_TRANSLATES = True
except ImportError:  # pragma: no cover - older cores, which is what we reject
    from homeassistant.exceptions import HomeAssistantError as ConfigEntryError  # type: ignore[import]
    # A core without `ConfigEntryError` also predates translated exceptions
    # (2024.4), so `HomeAssistantError.__init__` takes no `translation_*`
    # arguments. Passing them raises TypeError *instead of* the version message,
    # which is the one moment that message has to get through.
    _CONFIG_ENTRY_ERROR_TRANSLATES = False
try:  # HA 2023.10+
    from homeassistant.exceptions import ServiceValidationError  # type: ignore[import]
except ImportError:  # pragma: no cover - older cores
    from homeassistant.exceptions import HomeAssistantError as ServiceValidationError  # type: ignore[import]
from homeassistant.helpers.event import (  # type: ignore[import]
    async_track_time_interval,
    async_track_state_change_event,
)
import voluptuous as vol  # type: ignore[import]
from homeassistant.helpers import config_validation as cv, entity_registry as er, device_registry as dr # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession # type: ignore[import]
from .notification_rules import (
    build_clear_payload,
    coerce_targets,
    is_mobile_target,
    notify_tag_base,
)
from homeassistant.components.persistent_notification import (  # type: ignore[import]
    async_create as pn_async_create,
    async_dismiss as pn_async_dismiss,
)

from .const import (
    MINIMUM_HA_VERSION,
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
from .utils import (
    core_version_supported,
    BUSY_PRINT_STATES,
    ModelDetection,
    build_modify_material_payload,
    derive_activity_state,
)




_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "camera", "button", "number", "fan", "light", "image"]

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

def _core_version() -> tuple[int, int] | None:
    """The running Home Assistant version, or None if it cannot be read.

    MAJOR/MINOR are ints; PATCH_VERSION is a string that can read "0b3" on a
    beta, so it is deliberately ignored.
    """
    try:
        from homeassistant.const import (  # type: ignore[import]
            MAJOR_VERSION,
            MINOR_VERSION,
        )

        return (int(MAJOR_VERSION), int(MINOR_VERSION))
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug("Could not determine the Home Assistant version")
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Creality integration from a config entry."""
    # HACS refuses to install this version on an older core, but a manual or git
    # install bypasses that entirely -- and the failure would otherwise be a live
    # print card that quietly never appears. Fail with something actionable
    # instead. ConfigEntryError rather than ConfigEntryNotReady: retrying cannot
    # make the core newer.
    running = _core_version()
    if not core_version_supported(running, MINIMUM_HA_VERSION):
        minimum_text = ".".join(str(part) for part in MINIMUM_HA_VERSION)
        running_text = ".".join(str(part) for part in running or ()) or "unknown"
        if not _CONFIG_ENTRY_ERROR_TRANSLATES:
            # The only inline user-visible string in the integration, and it has
            # to be: this core cannot resolve a translation key, so the choice is
            # an English sentence or a TypeError. `strings.json` still carries the
            # translated version for every core that can use it.
            raise ConfigEntryError(
                f"ha_creality_ws requires Home Assistant {minimum_text} or newer; "
                f"this system is running {running_text}."
            )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="unsupported_ha_version",
            translation_placeholders={
                "minimum": minimum_text,
                "running": running_text,
            },
        )

    # Run migrations first
    _migrate_go2rtc_settings(hass, entry)
    
    host: str = entry.data["host"]
    
    # Handle power switch - only use if both enabled and entity is set
    power_switch_enabled = entry.options.get(CONF_POWER_SWITCH_ENABLED, False)
    power_switch = entry.options.get(CONF_POWER_SWITCH)
    effective_power_switch = power_switch if (power_switch_enabled and power_switch) else None
    
    _LOGGER.info("Power switch config: enabled=%s, entity=%s, effective=%s", 
                 power_switch_enabled, power_switch, effective_power_switch)
    
    coord = KCoordinator(
        hass, host=host, power_switch=effective_power_switch, config_entry=entry
    )

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
        
    # No MAC caching here: Creality printers do not report one in the JSON
    # payload. _cached_mac comes from zeroconf discovery instead.
         
    # Also re-cache if max temperature values are missing (migration from older versions)
    should_re_cache = should_re_cache or (
        entry.data.get("_cached_max_bed_temp") is None or
        entry.data.get("_cached_max_nozzle_temp") is None
    )

    # Also re-cache if LED brightness capability keys are missing (migration from
    # versions before LED dimming support). Check key presence, not value, since
    # led_pin is legitimately None for models without brightness control.
    should_re_cache = should_re_cache or (
        "_cached_has_brightness_control" not in entry.data or
        "_cached_led_pin" not in entry.data
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
                new_data["_cached_has_brightness_control"] = printermodel.has_brightness_control
                new_data["_cached_led_pin"] = printermodel.led_pin
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
                # No brightness control until we can detect the model online.
                new_data["_cached_has_brightness_control"] = False
                new_data["_cached_led_pin"] = None
                new_data["_cached_has_chamber_sensor"] = False
                new_data["_cached_has_chamber_control"] = False
                # Legacy mirrors
                new_data["_cached_has_box_sensor"] = False
                new_data["_cached_has_box_control"] = False
                new_data["_cached_camera_type"] = "mjpeg"
            elif (
                "_cached_has_brightness_control" not in new_data
                or "_cached_led_pin" not in new_data
            ):
                # Migration from before LED-dimming support: the printer is
                # offline so we can't read live telemetry, but the model was
                # cached on a previous online run. Derive the brightness
                # capability from that cached model so the light exposes dimming
                # without waiting for the printer to be online again.
                cached_model = ModelDetection({
                    "model": new_data.get("_cached_model"),
                    "modelVersion": new_data.get("_cached_model_version"),
                })
                new_data["_cached_has_brightness_control"] = cached_model.has_brightness_control
                new_data["_cached_led_pin"] = cached_model.led_pin
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            
            # Migrate go2rtc settings even when printer is off
            _migrate_go2rtc_settings(hass, entry)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coord



    # Register the Lovelace card (non-fatal on failure)
    try:
        card_register = CrealityCardRegistration(hass)
        await card_register.async_register()
    except Exception as exc:
        _LOGGER.warning("Lovelace card registration skipped due to error: %s", exc)

    # Listener for options updates
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Live-notification buttons. Registered unconditionally rather than behind
    # the option: the action ids are namespaced per config entry and the handler
    # matches them exactly, so with buttons switched off nothing can fire (no
    # notification carries them) and there is no listener lifecycle to get wrong.
    async def _on_notification_action(event) -> None:
        action = event.data.get("action")
        if action:
            await coord.async_handle_notification_action(action)

    entry.async_on_unload(
        hass.bus.async_listen("mobile_app_notification_action", _on_notification_action)
    )

    # Periodic state checker
    # Home Assistant runs a plain sync job in an executor thread. This one
    # reaches `hass.async_create_task` and `hass.loop.time()` through
    # `notifier_tick`, which are loop-only APIs. It does no blocking work, so
    # the loop is where it belongs.
    @callback
    def _interval_check(_now) -> None:
        coord.check_stale()
        # Every live-card transition is otherwise driven by an incoming frame,
        # so a printer that goes silent mid-print would leave a card counting
        # down on the phone forever. Reuses this interval; no new timer.
        coord.notifier_tick()
        # Listener updates are left to the coordinator, which throttles them.
    
    cancel_interval = async_track_time_interval(
        hass, _interval_check, timedelta(seconds=max(5, STALE_AFTER_SECS // 3))
    )
    entry.async_on_unload(cancel_interval)

    # Watcher for power switch state changes
    def _watch_power_switch(entity_id: str | None) -> Callable:
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
            # A byte-identical duplicate of sensor "model_info": same field,
            # same attributes. Removed rather than left orphaned.
            ("sensor", f"{host}-system"),
        ]
        for domain_name, unique in legacy:
            ent_id = reg.async_get_entity_id(domain_name, DOMAIN, unique)
            if ent_id:
                reg.async_remove(ent_id)
    except Exception as exc:
        _LOGGER.debug("Legacy entity cleanup skipped: %s", exc)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Asking the service registry, the same way _register_custom_services does,
    # rather than keeping a flag: hass.data[DOMAIN] is keyed by entry id and a
    # sentinel in there is indistinguishable from a coordinator.
    if not hass.services.has_service(DOMAIN, "diagnostic_dump"):
        await _register_diagnostic_service(hass)

    # Register custom services
    await _register_custom_services(hass)
    
    _LOGGER.info("ha_creality_ws: setup complete")
    return True


def _coordinators_for_devices(
    hass: HomeAssistant, device_ids: str | list[str] | None
) -> list[KCoordinator]:
    """Resolve service ``device_id`` targets to coordinators.

    Shared by every device-targeted service so they agree on what a target means.
    A falsy ``device_ids`` selects every configured printer, which is what
    ``request_cfs_info`` relies on for its "refresh everything" behaviour.
    """
    target_entry_ids: set[str] = set()

    if device_ids:
        # The device selector yields a list, but YAML callers often pass a string.
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        dev_reg = dr.async_get(hass)
        for dev_id in device_ids:
            device = dev_reg.async_get(dev_id)
            if not device:
                _LOGGER.warning("No such device: %s", dev_id)
                continue
            target_entry_ids.update(device.config_entries)

        if not target_entry_ids:
            return []

    return [
        coord
        for entry_id, coord in hass.data[DOMAIN].items()
        if isinstance(coord, KCoordinator)
        and (not target_entry_ids or entry_id in target_entry_ids)
    ]


async def _register_custom_services(hass: HomeAssistant) -> None:
    """Register custom services for the integration."""

    async def request_cfs_info(call: ServiceCall) -> None:
        """Service to manually request CFS info from all or specific printers."""
        targets = _coordinators_for_devices(hass, call.data.get("device_id"))

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
            notification_id="cfs_request_result",
        )

    async def set_cfs_material(call: ServiceCall) -> None:
        """Write filament metadata to one CFS slot.

        This is the only *write* path into the CFS. The payload shape comes from
        @buzato's work in PR #75, confirmed against real hardware there but not
        documented by Creality, so the outgoing value and the printer's echo are
        both logged (see ``_log_material_echo``).
        """
        # An explicit target is mandatory here. _coordinators_for_devices reads a
        # falsy value as "every printer", which request_cfs_info wants but a write
        # service must not do: `device_id: []` passes the schema and would
        # otherwise write this payload to every configured printer.
        requested = call.data.get("device_id")
        if not requested:
            raise ServiceValidationError(
                "set_cfs_material requires a device_id; refusing to write to "
                "every configured printer."
            )

        targets = _coordinators_for_devices(hass, requested)
        if not targets:
            raise ServiceValidationError(
                "No Creality printer matched the selected device."
            )

        box_id = call.data["box_id"]
        slot_id = call.data["slot_id"]

        try:
            payload = build_modify_material_payload(
                box_id=box_id,
                slot_id=slot_id,
                material_type=call.data["type"],
                name=call.data.get("name"),
                vendor=call.data.get("vendor"),
                color=call.data.get("color"),
                min_temp=call.data.get("min_temp"),
                max_temp=call.data.get("max_temp"),
                pressure=call.data.get("pressure"),
                rfid=call.data.get("rfid"),
            )
        except ValueError as exc:
            # Bad input, not a printer failure -- surface it on the call itself.
            raise ServiceValidationError(str(exc)) from exc

        # Check every target before writing to any of them, so a busy second
        # printer cannot leave the first one already modified.
        # The card guards this too, but automations and Developer Tools do not go
        # through the card.
        for coord in targets:
            # The *activity* state, matching `KCoordinator._job_state`: the
            # display state reports "error" for any non-zero `err.errcode`,
            # including one the printer never clears, and "error" is not in
            # BUSY_PRINT_STATES -- so a printer that was printing with a stale
            # code sailed through this guard and took a modifyMaterial write
            # mid-print, which is the exact thing being guarded against.
            state = derive_activity_state(
                coord.data or {},
                power_off=coord.power_is_off(),
                available=coord.available,
                paused_flag=coord.paused_flag(),
            )
            if state in BUSY_PRINT_STATES:
                raise ServiceValidationError(
                    f"{coord.client.host} is {state}; refusing to change CFS "
                    "material while the printer is busy."
                )

        for coord in targets:
            host = coord.client.host
            try:
                _LOGGER.debug("Sending modifyMaterial to %s: %s", host, payload)
                await coord.client.send_set_retry(modifyMaterial=payload)
            except Exception as exc:
                _LOGGER.error("Failed to set CFS material for %s: %s", host, exc)
                pn_async_create(
                    hass,
                    title="CFS Material Update Failed",
                    message=f"Failed to update material on {host}: {exc}",
                    # Per-host: device_id accepts a list, and a shared id would
                    # leave only the last printer's result visible.
                    notification_id=f"cfs_material_error_{host}",
                )
                continue

            # Clear any earlier failure for this printer, so a successful retry
            # does not leave "Update Failed" and "Updated" on screen together.
            pn_async_dismiss(hass, f"cfs_material_error_{host}")
            pn_async_create(
                hass,
                title="CFS Material Updated",
                message=(
                    f"Box {box_id} slot {slot_id} on {host} updated."
                ),
                notification_id=f"cfs_material_update_{host}",
            )
            hass.async_create_task(_log_material_echo(coord, payload))

    async def _log_material_echo(coord: KCoordinator, payload: dict[str, Any]) -> None:
        """Log what the printer actually stored after a material write.

        Creality streams colours as seven hex characters (a pad character plus
        RRGGBB) but accepts six on write, and no public documentation confirms how
        the other fields are echoed. Logging the round trip means the first user
        with real CFS hardware produces the evidence in their debug log instead of
        us guessing -- see utils.normalize_color_hex and issues #113/#117.
        """
        try:
            await asyncio.sleep(1.5)
            await coord.client.request_boxs_info()
            await asyncio.sleep(1.5)

            boxes = (coord.data or {}).get("boxsInfo", {}).get("materialBoxs", [])
            for box in boxes:
                if box.get("id") != payload["boxId"]:
                    continue
                for slot in box.get("materials", []):
                    if slot.get("id") != payload["id"]:
                        continue
                    _LOGGER.debug(
                        "modifyMaterial echo for %s box %s slot %s: sent %s, printer "
                        "now reports %s",
                        coord.client.host,
                        payload["boxId"],
                        payload["id"],
                        payload,
                        slot,
                    )
                    return

            _LOGGER.debug(
                "modifyMaterial echo for %s: box %s slot %s not present in boxsInfo "
                "after the write",
                coord.client.host,
                payload["boxId"],
                payload["id"],
            )
        except Exception as exc:  # pragma: no cover - diagnostics only
            _LOGGER.debug("Could not read back CFS material echo: %s", exc)

    # Bounds mirror services.yaml and the CFS card's edit form so all three agree.
    set_cfs_material_schema = vol.Schema(
        {
            vol.Required("device_id"): vol.Any(cv.string, [cv.string]),
            # No max: box_id is printer-reported and an external unit can
            # present a high id, so an artificial ceiling made real slots
            # unwritable. See the note in services.yaml.
            vol.Required("box_id"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Required("slot_id"): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
            vol.Required("type"): cv.string,
            vol.Optional("name"): cv.string,
            vol.Optional("vendor"): cv.string,
            # A plain hex string, not a color_rgb selector: that selector returns
            # [r, g, b], which the printer does not understand.
            vol.Optional("color"): cv.string,
            vol.Optional("min_temp"): vol.All(
                vol.Coerce(float), vol.Range(min=150, max=300)
            ),
            vol.Optional("max_temp"): vol.All(
                vol.Coerce(float), vol.Range(min=150, max=350)
            ),
            vol.Optional("pressure"): vol.All(
                vol.Coerce(float), vol.Range(min=0, max=1)
            ),
            vol.Optional("rfid"): cv.string,
        }
    )

    if not hass.services.has_service(DOMAIN, "request_cfs_info"):
        hass.services.async_register(DOMAIN, "request_cfs_info", request_cfs_info)

    if not hass.services.has_service(DOMAIN, "set_cfs_material"):
        hass.services.async_register(
            DOMAIN,
            "set_cfs_material",
            set_cfs_material,
            schema=set_cfs_material_schema,
        )


async def _register_diagnostic_service(hass: HomeAssistant) -> None:
    """Register diagnostic service - outputs all data to logs (no file storage)."""
    
    async def diagnostic_dump(call: ServiceCall) -> None:
        """Collect and log telemetry data for all printers."""
        try:
            # Get all coordinators (all printer instances)
            coordinators: list[tuple[str, KCoordinator]] = []
            for entry_id, coord in hass.data[DOMAIN].items():
                if isinstance(coord, KCoordinator):
                    coordinators.append((entry_id, coord))
            
            if not coordinators:
                _LOGGER.error("No Creality printers found to dump data from")
                return
            
            # Create diagnostic data structure
            diagnostic_data = {
                "timestamp": dt_util.utcnow().isoformat(),
                "home_assistant_version": HA_VERSION,
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
    # Fallback to simple name/IP matching logic or legacy checks
    # If users rely on hostname, IP-based recovery without MAC is dangerous (DHCP shuffle).



async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply an options change: in place where that is enough, else a reload."""
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coord is not None:
        # A change confined to the notification settings needs no reload. One
        # would drop the WebSocket, flip every entity unavailable and restart
        # the camera stream, all to reword a notification -- and the options
        # flow saves each page as it is submitted, so that used to happen once
        # per page while someone was still editing.
        try:
            if coord.notifications_only_change(entry.options):
                coord.apply_notification_options(entry.options)
                return
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to apply notification options; reloading")

        # Before the reload wipes the in-memory live-card state: if the card is
        # being switched off, this is the last moment anything knows one is still
        # showing on a phone.
        try:
            coord.notify_options_changed(entry.options)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Failed to reconcile the live card with new options")

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
async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take this printer's notifications off every phone as it is deleted.

    Unload deliberately leaves them alone, because `options_update_listener`
    reloads the entry on any options change and dismissing there would make the
    card flicker every time an unrelated setting is toggled. Removal is the one
    teardown that is not a reload, and it is final: nothing will ever push to
    these tags again, so a live card left behind would sit on a phone showing a
    printer that no longer exists in Home Assistant.

    Runs after the coordinator is gone, so it works from the entry alone.
    """
    targets = coerce_targets(entry.options)
    if not targets:
        return

    tag_base = notify_tag_base(entry.entry_id)
    payloads = [
        build_clear_payload(f"{tag_base}_{suffix}")
        for suffix in ("live", "soon", "alert")
    ]

    for target in targets:
        # The dismiss marker renders as literal body text anywhere but the
        # companion app, so a non-mobile target must never receive one.
        if not is_mobile_target(target) or "." not in target:
            continue
        domain, service = target.split(".", 1)
        for payload in payloads:
            try:
                await hass.services.async_call(
                    domain,
                    service,
                    {"message": payload["message"], "data": payload["data"]},
                )
            except Exception:  # pylint: disable=broad-except
                # A phone that has since been removed must not stop the others,
                # and this is the last chance to tidy up either way.
                _LOGGER.debug(
                    "Could not dismiss notifications on %s during removal",
                    target,
                    exc_info=True,
                )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coord: KCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coord.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # The Lovelace resources and the static paths are deliberately left in
    # place. Removing a resource would break any dashboard still referencing the
    # card while the integration is merely reloading, and HA has no way to
    # unregister a static path anyway.
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
