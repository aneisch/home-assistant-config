from __future__ import annotations
import logging
import asyncio
import json
from datetime import timedelta
from collections.abc import Callable
from typing import Any



from homeassistant.config_entries import ConfigEntry, OperationNotAllowed # type: ignore[import]
from homeassistant.const import EVENT_HOMEASSISTANT_STOP  # type: ignore[import]
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback # type: ignore[import]
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError  # type: ignore[import]
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
from homeassistant.helpers.service import async_register_admin_service  # type: ignore[import]
from homeassistant.helpers.translation import async_get_translations  # type: ignore[import]
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
    CONF_HOST,
    MINIMUM_HA_VERSION,
    DOMAIN, 
    STALE_AFTER_SECS, 
    CONF_POWER_SWITCH,
    CONF_POWER_SWITCH_ENABLED,
    CONF_GO2RTC_URL,
    CONF_GO2RTC_PORT,
)
from .coordinator import KCoordinator
from .frontend import CrealityCardRegistration
from .utils import (
    PLACEHOLDER_MODEL,
    core_version_supported,
    BUSY_PRINT_STATES,
    MaterialValueError,
    ModelDetection,
    build_modify_material_payload,
    derive_activity_state,
    camera_type_to_keep,
    detect_camera_type,
)




_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "camera", "button", "number", "fan", "light", "image"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Import integration version from manifest

async def _get_integration_version(hass: HomeAssistant) -> str:
    """The integration's version, as Home Assistant loaded it (R37).

    From the loader's cached manifest rather than reading manifest.json again
    in an executor job at every setup.
    """
    from homeassistant.loader import async_get_integration  # pylint: disable=import-outside-toplevel

    try:
        return str((await async_get_integration(hass, DOMAIN)).version or "0.0.0")
    except Exception:  # pylint: disable=broad-except
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
    
    # No longer strips a stored localhost:11984 (the 0.9.0 "bad default").
    # The camera already tells Home Assistant's own go2rtc from a stand-alone
    # one on that pair (it checks whether HA's go2rtc is loaded), and the
    # strip ran first, at every setup: a Core install whose own go2rtc sits on
    # the default pair lost the setting before the camera could read it, and
    # failed with "go2rtc component not loaded" (R18).

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


@callback
def _async_follow_host(hass: HomeAssistant, entry: ConfigEntry, host: str) -> None:
    """Move this entry's device and entities onto `host` after it changed.

    Entity unique ids and the device identifier embed the host
    (`"<host>-<key>"`, `(DOMAIN, host)`). A new IP, from the options
    Connection page or a rediscovery, used to recreate every entity with a
    `_2` id on a second device, stranding the originals with their history,
    their customisations and every automation that named them (#39).

    Runs at every setup, so it covers any way the host can change. Where an
    entity already exists under the new id (a registry split by that bug in
    an earlier version), that entity is left alone: merging in either
    direction would rename entities someone may have rebuilt automations on.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    old_hosts: set[str] = set()
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    # Searched among this entry's own devices, not with a registry lookup:
    # identifiers are scoped per entry, and the lookup that ignored that is
    # deprecated.
    target_exists = any((DOMAIN, host) in d.identifiers for d in devices)
    for device in devices:
        ours = {i for i in device.identifiers if i[0] == DOMAIN}
        stale = {i[1] for i in ours if i[1] != host}
        if not stale:
            continue
        old_hosts |= stale
        if target_exists:
            # INFO, not WARNING: it is a standing state, logged on every start.
            _LOGGER.info(
                "Printer moved to %s, but a device for that address already "
                "exists; leaving the device for %s as it is",
                host,
                ", ".join(sorted(stale)),
            )
            continue
        dev_reg.async_update_device(
            device.id,
            new_identifiers=(device.identifiers - ours) | {(DOMAIN, host)},
        )

    moved = conflicts = 0
    for old in old_hosts:
        prefix = f"{old}-"
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if not reg_entry.unique_id.startswith(prefix):
                continue
            new_uid = f"{host}-{reg_entry.unique_id[len(prefix):]}"
            if ent_reg.async_get_entity_id(reg_entry.domain, DOMAIN, new_uid):
                conflicts += 1
                continue
            ent_reg.async_update_entity(reg_entry.entity_id, new_unique_id=new_uid)
            moved += 1
    if old_hosts:
        _LOGGER.info(
            "Printer moved from %s to %s: kept %d entities%s",
            ", ".join(sorted(old_hosts)),
            host,
            moved,
            f" ({conflicts} already existed at the new address)" if conflicts else "",
        )

    # The entry's own unique id is the host too. Left behind, it blocks adding
    # another printer that later gets the old address, and lets this printer
    # be added a second time at the new one.
    if entry.unique_id != host and not any(
        other.unique_id == host
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry.entry_id
    ):
        hass.config_entries.async_update_entry(entry, unique_id=host)


def _derive_led_pin(data: dict[str, Any]) -> bool:
    """Fill in whether the light dims from the cached model, if not cached yet.

    For an entry cached before LED dimming existed (#102), or before its model
    was known to dim (#136), set up while the printer is offline: the model
    alone says whether the light can dim, so it need not wait for the printer
    to come online. True if `data` changed.
    """
    if not data.get("_cached_model"):
        return False
    cached_model = ModelDetection({
        "model": data.get("_cached_model"),
        "modelVersion": data.get("_cached_model_version"),
    })
    if "_cached_has_brightness_control" in data and "_cached_led_pin" in data and (
        data["_cached_led_pin"] or not cached_model.led_pin
    ):
        return False
    data["_cached_has_brightness_control"] = cached_model.has_brightness_control
    data["_cached_led_pin"] = cached_model.led_pin
    return True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register the actions once, whatever happens to the entries (R34).

    Registered from the first entry's setup, they did not exist while that
    entry was failing to load, so an automation calling one failed with
    "action not found" instead of saying which printer was the problem.
    """
    await _register_diagnostic_service(hass)
    await _register_custom_services(hass)
    return True


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
    # Before any platform registers an entity under the new address.
    _async_follow_host(hass, entry, host)

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
    except Exception as exc:
        await coord.async_stop()
        raise ConfigEntryNotReady(str(exc)) from exc
    # Registered at once, so a setup that fails further down does not leave
    # the client task running with no entry behind it (R31).
    entry.async_on_unload(coord.async_stop)

    # Entries are not unloaded when Home Assistant stops, so without this the
    # client kept reconnecting through shutdown until the loop was torn down
    # under it, and the printer never got a close frame (R39).
    async def _stop_client(_event) -> None:
        await coord.async_stop()

    # async_listen, not async_listen_once: Home Assistant stops once anyway,
    # and a one-time listener that has fired cannot be removed again, so an
    # unload after the stop event logged an error.
    entry.async_on_unload(
        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, _stop_client)
    )
    # No wait here. The entities come from the capability cache and fill in
    # as telemetry arrives (late discovery covers anything gated on it). An
    # unconditional 15 s wait for a printer that was switched off held up
    # Home Assistant's startup by that much per printer (R31); the cache block
    # below still waits when it actually has something to learn.

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
        # The one wait at setup, and only when there is something to learn:
        # first setup, an integration upgrade, or a moved printer.
        if not coord.power_is_off():
            ok = await coord.wait_first_connect(timeout=15.0)
            if not ok:
                _LOGGER.warning("Initial connect not confirmed; will retry in background")
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
                model = printermodel.resolved_model() or entry.data.get("_cached_model") or PLACEHOLDER_MODEL
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
                # -- except control on the K1 family, which has no chamber
                # heater although a K1C reports `targetBoxTemp` (R71).
                if "targetBoxTemp" in d and not printermodel.is_k1_family:
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
                
                # Re-detected from the evidence every time, not kept once set:
                # a firmware update can move a K1C from MJPEG to WebRTC (#46).
                # A direct-WebRTC verdict from before 0.9.10 is retried once (#134).
                new_data["_cached_camera_type"] = detect_camera_type(
                    d, camera_type_to_keep(entry.data.get("_cached_camera_type"), cached_version)
                )
                
                hass.config_entries.async_update_entry(entry, data=new_data)
                _LOGGER.info(
                    "Device info cached: model=%s, camera=%s, version=%s",
                    model, new_data.get("_cached_camera_type"), current_version
                )
                
                # Migrate go2rtc settings if needed
                _migrate_go2rtc_settings(hass, entry)
            else:
                # Offline with no power switch to say so. Nothing is learnt
                # live, but a cached model still says whether the light dims
                # (#102); the rest is re-cached once the printer answers.
                new_data = dict(entry.data)
                if _derive_led_pin(new_data):
                    hass.config_entries.async_update_entry(entry, data=new_data)
        else:
            # Printer is off - update version only, keep existing cached data if available
            _LOGGER.info(
                "Printer is off, updating version only (keeping existing cached data if available)"
            )
            new_data = dict(entry.data)
            new_data["_device_info_cached"] = True
            # A direct-WebRTC verdict due its retry (#134) keeps the old
            # version, so the first start the printer answers at re-detects it.
            cached_camera = new_data.get("_cached_camera_type")
            if camera_type_to_keep(cached_camera, cached_version) == cached_camera:
                new_data["_cached_version"] = current_version

            # Only set defaults if this is first-time setup (no cached model exists)
            if not new_data.get("_cached_model"):
                new_data["_cached_model"] = PLACEHOLDER_MODEL
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
            else:
                _derive_led_pin(new_data)
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            
            # Migrate go2rtc settings even when printer is off
            _migrate_go2rtc_settings(hass, entry)

    # The device-info cache above only refreshes on an upgrade, but the camera
    # can change with the printer's firmware. Checked on every start the
    # printer is talking at, before the camera platform reads it.
    live_camera = detect_camera_type(coord.data, entry.data.get("_cached_camera_type"))
    if live_camera and live_camera != entry.data.get("_cached_camera_type"):
        _LOGGER.info(
            "Camera type for %s is now %s (was %s)",
            host,
            live_camera,
            entry.data.get("_cached_camera_type"),
        )
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "_cached_camera_type": live_camera}
        )

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
        # A configured switch that has gone missing never sends a state
        # change; this is where the end of its grace period is noticed.
        if coord._switch_missing_since is not None:  # pylint: disable=protected-access
            hass.async_create_task(coord.async_recheck_missing_switch())
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
        # The chamber target a K1 got because it reports targetBoxTemp; no
        # K1-family printer has a chamber heater, so it never did anything (R71).
        if ModelDetection.from_cache(entry.data, coord.data).is_k1_family:
            legacy.append(("number", f"{host}-box_target"))
        for domain_name, unique in legacy:
            ent_id = reg.async_get_entity_id(domain_name, DOMAIN, unique)
            if ent_id:
                reg.async_remove(ent_id)
    except Exception as exc:
        _LOGGER.debug("Legacy entity cleanup skipped: %s", exc)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("ha_creality_ws: setup complete")
    return True


async def _common_strings(hass: HomeAssistant) -> dict[str, str]:
    """The integration's `common` strings in the server's language (R33).

    Persistent notifications are composed here, so, like the phone
    notifications, they can only use the server's language.
    """
    language = getattr(getattr(hass, "config", None), "language", None) or "en"
    prefix = f"component.{DOMAIN}.common."
    try:
        raw = await async_get_translations(hass, language, "common", {DOMAIN})
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Could not load the integration's strings")
        return {}
    return {key[len(prefix):]: value for key, value in raw.items() if key.startswith(prefix)}


def _fill(strings: dict[str, str], key: str, /, **values: str) -> str:
    """One string with its placeholders filled; the key itself if it is missing."""
    try:
        return strings[key].format(**values)
    except (KeyError, IndexError, ValueError):
        _LOGGER.warning("String %r is missing or does not match its placeholders", key)
        return key


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
        for entry_id, coord in hass.data.get(DOMAIN, {}).items()
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

        asked: list[str] = []
        failed: list[str] = []
        for coord in targets:
            try:
                _LOGGER.info("Manually requesting CFS info for %s", coord.client.host)
                await coord.client.request_boxs_info()
                asked.append(coord.client.host)
            except Exception as exc:
                _LOGGER.error("Failed to request CFS info for %s: %s", coord.client.host, exc)
                failed.append(coord.client.host)

        # Nothing to say on success: the CFS sensors update, and the card that
        # calls this after every save already shows its own result. A
        # notification each time left one in the bell per save (R76).
        if not failed:
            pn_async_dismiss(hass, "cfs_request_result")
            return
        strings = await _common_strings(hass)
        pn_async_create(
            hass,
            title=_fill(strings, "cfs_info_title"),
            message=_fill(strings, "cfs_info_failed", printers=", ".join(failed)),
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
                translation_domain=DOMAIN, translation_key="cfs_material_needs_device"
            )

        targets = _coordinators_for_devices(hass, requested)
        if not targets:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="no_printer_matched"
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
        except MaterialValueError as exc:
            # Bad input, not a printer failure -- surface it on the call itself.
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=exc.key,
                translation_placeholders=exc.placeholders,
            ) from exc

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
                    translation_domain=DOMAIN,
                    translation_key="cfs_material_printer_busy",
                    translation_placeholders={"printer": coord.client.host},
                )

        strings = await _common_strings(hass)
        # 1-based, as the sensors name the slots (R28).
        where = {"box": str(box_id), "slot": str(slot_id + 1)}
        failed: list[str] = []
        for coord in targets:
            host = coord.client.host
            try:
                _LOGGER.debug("Sending modifyMaterial to %s: %s", host, payload)
                await coord.client.send_set_retry(modifyMaterial=payload)
            except Exception as exc:
                failed.append(host)
                _LOGGER.error("Failed to set CFS material for %s: %s", host, exc)
                pn_async_create(
                    hass,
                    title=_fill(strings, "cfs_material_failed_title"),
                    message=_fill(strings, "cfs_material_failed", printer=host, **where),
                    # Per-host: device_id accepts a list, and a shared id would
                    # leave only the last printer's result visible.
                    notification_id=f"cfs_material_error_{host}",
                )
                continue

            # Clear any earlier failure for this printer. Success itself posts
            # nothing (R76): the card shows its own result, and an automation
            # learns of a failure from the raise below.
            pn_async_dismiss(hass, f"cfs_material_error_{host}")
            hass.async_create_task(_log_material_echo(coord, payload))

        # After every target has been tried: one unreachable printer must not
        # stop the others being written, but the caller has to learn that a
        # write failed. Returning normally made the CFS card report "Saved"
        # for a change that never reached the printer (R19).
        if failed:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cfs_material_write_failed",
                translation_placeholders={"printers": ", ".join(failed)},
            )

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
        hass.services.async_register(
            DOMAIN,
            "request_cfs_info",
            request_cfs_info,
            schema=vol.Schema(
                {vol.Optional("device_id"): vol.Any(cv.string, [cv.string])}
            ),
        )

    if not hass.services.has_service(DOMAIN, "set_cfs_material"):
        hass.services.async_register(
            DOMAIN,
            "set_cfs_material",
            set_cfs_material,
            schema=set_cfs_material_schema,
        )


async def _register_diagnostic_service(hass: HomeAssistant) -> None:
    """Register diagnostic service - outputs all data to logs (no file storage)."""
    
    async def diagnostic_dump(call: ServiceCall) -> ServiceResponse:
        """Collect every printer's diagnostics, log them and return them.

        Returned as the action's response (Developer Tools > Actions shows it),
        which is what the README, the bug form and the issue bot always told
        reporters to copy; before, the data only went to the log. Redacted
        unless `include_sensitive_data` is set, an option that used to be
        accepted and ignored.
        """
        from .diagnostics import async_collect, redact  # pylint: disable=import-outside-toplevel

        data = await async_collect(hass, await _get_integration_version(hass))
        if not data["printers"]:
            _LOGGER.error("No Creality printers found to dump data from")
            return data
        if not call.data.get("include_sensitive_data"):
            data = redact(hass, data)
        json_output = json.dumps(data, indent=2, ensure_ascii=False)
        # Still logged, for anyone following the older instructions.
        _LOGGER.warning(
            "=== CREALITY DIAGNOSTIC DATA START ===\n%s\n=== CREALITY DIAGNOSTIC DATA END ===",
            json_output,
        )
        strings = await _common_strings(hass)
        pn_async_create(
            hass,
            title=_fill(strings, "diagnostic_title"),
            message=_fill(strings, "diagnostic_collected", printers=str(len(data["printers"]))),
            notification_id="creality_diagnostic_data",
        )
        return data
    
    # Register the service
    schema = vol.Schema({
        vol.Optional("include_sensitive_data", default=False): bool,
    })
    
    # Admins only: the response can be unredacted (`include_sensitive_data`),
    # and carries camera URLs and tokens for every printer. Automations run
    # without a user and are unaffected.
    async_register_admin_service(
        hass,
        DOMAIN,
        "diagnostic_dump",
        diagnostic_dump,
        schema=schema,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    _LOGGER.info("Diagnostic service registered: ha_creality_ws.diagnostic_dump")
    # Fallback to simple name/IP matching logic or legacy checks
    # If users rely on hostname, IP-based recovery without MAC is dangerous (DHCP shuffle).



async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply an options change: in place where that is enough, else a reload."""
    coord = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coord is not None and coord.consume_own_data_write(entry):
        # The coordinator refreshing its own cache, e.g. a new firmware
        # version (R40): nothing to reload.
        return
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
    reloads the entry on most options changes and dismissing there would make
    the card flicker every time an unrelated setting is toggled. Removal is the one
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
    # Platforms first: if one refuses to unload, the entry stays loaded, and
    # it must not be left with its client already stopped (R31).
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await coord.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)

    # The Lovelace resources and the static paths are deliberately left in
    # place. Removing a resource would break any dashboard still referencing the
    # card while the integration is merely reloading, and HA has no way to
    # unregister a static path anyway.
    return unload_ok


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device) -> bool:
    """Allow removing a device only once this printer no longer uses it (R35).

    That is a device left at an old address, such as one an earlier version
    doubled when the printer moved (#39). The printer's current device would
    come straight back: removing it used to be allowed and to wipe the cached
    model and MAC address, which reloaded the entry and re-created the device
    without its customisations, and lost the MAC that rediscovery uses to
    follow the printer to a new address. Removing the printer is done by
    deleting its entry.
    """
    current = (DOMAIN, entry.data.get(CONF_HOST))
    in_use = current in getattr(device, "identifiers", set())
    _LOGGER.info(
        "ha_creality_ws: request to remove device %s for entry %s: %s",
        getattr(device, "id", device),
        entry.entry_id,
        "refused, it is the printer's current device" if in_use else "allowed",
    )
    return not in_use
