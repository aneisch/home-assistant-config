from __future__ import annotations
import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urlparse
from .utils import extract_host_from_zeroconf as util_extract_host_from_zeroconf
import voluptuous as vol
from homeassistant import config_entries #type: ignore[import]
from homeassistant.data_entry_flow import FlowResult #type: ignore[import]
from homeassistant.helpers import selector #type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession #type: ignore[import]
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_NAME,
    DEFAULT_NAME,
    WS_PORT,
    WEBRTC_URL_TEMPLATE,
    WEBRTC_CALL_ROOT_URL_TEMPLATE,
    CONF_POWER_SWITCH,
    CONF_POWER_SWITCH_ENABLED,
    CONF_CAMERA_MODE,
    CAM_MODE_AUTO,
    CAM_MODE_MJPEG,
    CAM_MODE_WEBRTC,
    CAM_MODE_WEBRTC_DIRECT,
    CAM_MODE_CUSTOM,
    CONF_GO2RTC_URL,
    CONF_GO2RTC_PORT,
    CONF_CUSTOM_CAMERA_URL,
    DEFAULT_GO2RTC_URL,
    DEFAULT_GO2RTC_PORT,
    CONF_NOTIFY_DEVICE,
    CONF_NOTIFY_COMPLETED,
    CONF_NOTIFY_ERROR,
    CONF_NOTIFY_MINUTES_TO_END,
    CONF_MINUTES_TO_END_VALUE,
    CONF_POLLING_RATE,
    DEFAULT_POLLING_RATE,
)
from .utils import ModelDetection

_LOGGER = logging.getLogger(__name__)

async def _probe_tcp(host: str, port: int, timeout: float = 2.5) -> bool:
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def _probe_webrtc_signaling(hass, url: str, timeout: float = 1.5) -> bool:
    """Probe the Creality WebRTC signaling endpoint.
    
    Returns:
        bool: True if WebRTC signaling is available, False otherwise
    """
    session = async_get_clientsession(hass)
    try:
        async with session.head(url, timeout=timeout) as resp:
            if resp.status in (200, 204, 405):
                return True
    except Exception:
        pass
    try:
        async with session.get(url, timeout=timeout) as resp:
            if resp.status in (200, 204, 405):
                return True
    except Exception:
        return False
    return False


async def _has_webrtc_signaling(hass, host: str) -> bool:
    """Return True if any known Creality WebRTC signaling endpoint responds.

    Newer K1C firmwares expose the signaling endpoint on `/call` while K2-family
    printers use `/call/webrtc_local`; probe both before deciding.
    """
    for template in (WEBRTC_CALL_ROOT_URL_TEMPLATE, WEBRTC_URL_TEMPLATE):
        url = template.format(host=host)
        if await _probe_webrtc_signaling(hass, url, timeout=2.0):
            return True
    return False


def _extract_host_from_zeroconf(info: Any) -> Optional[str]:
    # Use shared helper for testability
    return util_extract_host_from_zeroconf(info)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    @staticmethod
    @config_entries.HANDLERS.register("options")
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            if not await _probe_tcp(host, WS_PORT):
                errors["base"] = "cannot_connect"
            else:
                title = user_input.get(CONF_NAME) or f"{DEFAULT_NAME} ({host})"
                return self.async_create_entry(title=title, data={CONF_HOST: host})

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": DEFAULT_NAME}
        )

    async def async_step_zeroconf(self, discovery_info: Any) -> FlowResult:
        from .utils import extract_info_from_zeroconf
        host, mac = extract_info_from_zeroconf(discovery_info)
        
        if not host:
            return self.async_abort(reason="cannot_connect")
            
        # Robust Update Check:
        # Check if an existing entry has this MAC address but a different IP.
        # If so, update it automatically and abort this new flow.
        if mac:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                cached_mac = entry.data.get("_cached_mac")
                if cached_mac and cached_mac.upper() == mac.upper():
                    if entry.data.get(CONF_HOST) != host:
                        _LOGGER.warning(
                            "Discovered printer with known MAC %s at new IP %s. Updating existing entry.", 
                            mac, host
                        )
                        self.hass.config_entries.async_update_entry(
                            entry, 
                            data={**entry.data, CONF_HOST: host, "_last_ip": host}
                        )
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(entry.entry_id)
                        )
                    return self.async_abort(reason="already_configured")

        # Standard check: if we already have this IP configured, abort
        if not await _probe_tcp(host, WS_PORT):
            return self.async_abort(reason="not_K")

        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        title = f"{DEFAULT_NAME} ({host})"
        return self.async_create_entry(title=title, data={CONF_HOST: host, "_cached_mac": mac})


# --------- Options Flow ---------
class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        # Avoid deprecated `self.config_entry = config_entry`; store private reference
        self._entry = config_entry
        # Working copy of options edited across sub-steps. Changes are staged here
        # by each section's submit and only persisted (one reload) by "Save and
        # apply". The menu back arrow returns without staging. None until first use.
        self._working: dict[str, Any] | None = None
        self._working_host: str | None = None

    def _ensure_working(self) -> None:
        """Initialize the working copy once per options-flow session."""
        if self._working is None:
            self._working = dict(self._entry.options)
            self._working_host = self._entry.data.get(CONF_HOST, "")

    async def _detect_camera_type(self) -> str:
        """Detect the camera type for this printer."""
        host = self._entry.data["host"]
        
        # Get the coordinator to access printer data
        try:
            coord = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
            if coord and coord.data:
                # Use model detection if we have telemetry data
                printermodel = ModelDetection(coord.data)
                
                # K2 family uses WebRTC
                if printermodel.is_k2_family:
                    _LOGGER.debug("ha_creality_ws: detected K2 family printer (WebRTC)")
                    return CAM_MODE_WEBRTC
                
                # K1 family, K1 Max, K1C, Creality Hi use MJPEG
                if printermodel.is_k1_family or printermodel.is_k1_max or printermodel.is_k1c or printermodel.is_creality_hi:
                    _LOGGER.debug("ha_creality_ws: detected MJPEG camera model")
                    return CAM_MODE_MJPEG
                
                # K1 SE and Ender V3 may have optional MJPEG
                if printermodel.is_k1_se or printermodel.is_ender_v3_family:
                    _LOGGER.debug("ha_creality_ws: detected optional camera model, trying MJPEG")
                    return CAM_MODE_MJPEG
        except Exception as exc:
            _LOGGER.debug("ha_creality_ws: failed to detect camera from telemetry: %s", exc)
        
        # Fallback: probe WebRTC signaling endpoints (both /call and /call/webrtc_local)
        if await _has_webrtc_signaling(self.hass, host):
            _LOGGER.debug("ha_creality_ws: detected WebRTC via probe")
            return CAM_MODE_WEBRTC

        # Default to MJPEG
        _LOGGER.debug("ha_creality_ws: defaulting to MJPEG")
        return CAM_MODE_MJPEG

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Top-level options menu (the hub each section returns to).

        Each settings group is its own step so its form is rebuilt fresh from the
        working copy every time it is opened — Home Assistant cannot re-render a
        single step when a dropdown changes, so conditional fields (e.g. the
        custom camera URL) would otherwise show stale based on the saved mode.

        Section submits stage changes into the working copy and come back here;
        "Save and apply" persists everything in one go. The dialog's back arrow
        returns to this menu without staging the current section.
        """
        self._ensure_working()
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "camera": "Camera",
                "notifications": "Notifications",
                "power": "Power switch",
                "connection": "Connection & performance",
                "save": "Save and apply",
            },
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Persist all staged changes (single reload)."""
        self._ensure_working()
        assert self._working is not None
        # Apply a host change to the entry data (separate from options).
        if self._working_host and self._working_host != self._entry.data.get(CONF_HOST):
            self.hass.config_entries.async_update_entry(
                self._entry, data={**self._entry.data, CONF_HOST: self._working_host}
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self._entry.entry_id)
            )
        return self.async_create_entry(title="", data=self._working)

    async def async_step_camera(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Camera settings. Conditional fields follow the selected mode."""
        self._ensure_working()
        assert self._working is not None
        errors: dict[str, str] = {}
        saved_mode = self._working.get(CONF_CAMERA_MODE, CAM_MODE_AUTO)
        # Mode to render fields for: the just-submitted one (so the error re-render
        # reveals the right fields), otherwise the staged/saved one.
        effective_mode = (user_input or {}).get(CONF_CAMERA_MODE, saved_mode)

        if user_input is not None:
            camera_mode = user_input.get(CONF_CAMERA_MODE, CAM_MODE_AUTO)
            if camera_mode == CAM_MODE_AUTO:
                camera_mode = await self._detect_camera_type()
                _LOGGER.info("ha_creality_ws: auto mode detected camera type: %s", camera_mode)

            self._working[CONF_CAMERA_MODE] = camera_mode

            if camera_mode == CAM_MODE_CUSTOM:
                custom_url = str(user_input.get(CONF_CUSTOM_CAMERA_URL) or "").strip()
                parsed = urlparse(custom_url)
                # Require a supported scheme and a host. http(s) -> MJPEG/snapshot;
                # rtsp/rtmp/srt -> ingested via go2rtc (see camera.async_setup_entry).
                if parsed.scheme.lower() not in ("http", "https", "rtsp", "rtmp", "srt") or not parsed.netloc:
                    errors[CONF_CUSTOM_CAMERA_URL] = "invalid_camera_url"
                    effective_mode = CAM_MODE_CUSTOM  # ensure the URL field is shown
                else:
                    self._working[CONF_CUSTOM_CAMERA_URL] = custom_url

            if camera_mode == CAM_MODE_WEBRTC:
                self._working[CONF_GO2RTC_URL] = (
                    str(user_input.get(CONF_GO2RTC_URL) or "").strip() or DEFAULT_GO2RTC_URL
                )
                port = user_input.get(CONF_GO2RTC_PORT)
                try:
                    self._working[CONF_GO2RTC_PORT] = int(port) if port is not None else DEFAULT_GO2RTC_PORT
                except (ValueError, TypeError):
                    self._working[CONF_GO2RTC_PORT] = DEFAULT_GO2RTC_PORT
            else:
                # Drop go2rtc settings for non-go2rtc modes so they don't linger.
                self._working.pop(CONF_GO2RTC_URL, None)
                self._working.pop(CONF_GO2RTC_PORT, None)

            if not errors:
                return await self.async_step_init()

        current_go2rtc_url = self._working.get(CONF_GO2RTC_URL, DEFAULT_GO2RTC_URL)
        current_go2rtc_port = self._working.get(CONF_GO2RTC_PORT, DEFAULT_GO2RTC_PORT)
        current_custom_url = self._working.get(CONF_CUSTOM_CAMERA_URL, "")
        show_go2rtc = effective_mode in (CAM_MODE_WEBRTC, CAM_MODE_AUTO)
        show_custom_url = effective_mode == CAM_MODE_CUSTOM

        schema_dict: dict[str, Any] = {
            vol.Optional(CONF_CAMERA_MODE, default=effective_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=CAM_MODE_AUTO, label="Auto (detect by model)"),
                        selector.SelectOptionDict(value=CAM_MODE_MJPEG, label="MJPEG (K1 family)"),
                        selector.SelectOptionDict(value=CAM_MODE_WEBRTC, label="WebRTC via go2rtc (K2 family)"),
                        selector.SelectOptionDict(value=CAM_MODE_WEBRTC_DIRECT, label="WebRTC direct, no go2rtc (alternative)"),
                        selector.SelectOptionDict(value=CAM_MODE_CUSTOM, label="Custom camera URL (MJPEG / RTSP)"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
        if show_go2rtc:
            schema_dict.update({
                vol.Optional(CONF_GO2RTC_URL, default=current_go2rtc_url): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(CONF_GO2RTC_PORT, default=current_go2rtc_port): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
                ),
            })
        if show_custom_url:
            schema_dict.update({
                vol.Optional(
                    CONF_CUSTOM_CAMERA_URL,
                    default=(current_custom_url or vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
            })

        return self.async_show_form(
            step_id="camera",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "camera_help": (
                    "Camera streaming mode. Auto detects from the printer model. "
                    "WebRTC via go2rtc is the default for K2-family printers; "
                    "WebRTC direct is an alternative that signals the printer itself "
                    "(no go2rtc) — try it if the default does not work, e.g. on newer "
                    "K1C firmware. Custom lets you point at any http(s) MJPEG/snapshot "
                    "URL or an rtsp:// stream (served via go2rtc). "
                    "Submit returns to the menu; use Save and apply there to apply changes."
                ),
            },
        )

    async def async_step_notifications(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Notification settings."""
        self._ensure_working()
        assert self._working is not None
        if user_input is not None:
            self._working.update(user_input)
            return await self.async_step_init()

        notify_device = self._working.get(CONF_NOTIFY_DEVICE)
        notify_completed = self._working.get(CONF_NOTIFY_COMPLETED, False)
        notify_error = self._working.get(CONF_NOTIFY_ERROR, False)
        notify_minutes_to_end = self._working.get(CONF_NOTIFY_MINUTES_TO_END, False)
        minutes_to_end_value = self._working.get(CONF_MINUTES_TO_END_VALUE, 5)

        notify_services = self.hass.services.async_services().get("notify", {})
        notify_service_options = [
            selector.SelectOptionDict(value=f"notify.{name}", label=name)
            for name in notify_services.keys()
        ]
        if notify_device and notify_device not in [o["value"] for o in notify_service_options]:
            notify_service_options.append(selector.SelectOptionDict(value=notify_device, label=notify_device))

        schema_dict: dict[str, Any] = {
            vol.Optional(CONF_NOTIFY_DEVICE, default=notify_device or vol.UNDEFINED): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_service_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Optional(CONF_NOTIFY_COMPLETED, default=notify_completed): selector.BooleanSelector(),
            vol.Optional(CONF_NOTIFY_ERROR, default=notify_error): selector.BooleanSelector(),
            vol.Optional(CONF_NOTIFY_MINUTES_TO_END, default=notify_minutes_to_end): selector.BooleanSelector(),
            vol.Optional(CONF_MINUTES_TO_END_VALUE, default=minutes_to_end_value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=60, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="min")
            ),
        }
        return self.async_show_form(step_id="notifications", data_schema=vol.Schema(schema_dict))

    async def async_step_power(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Power switch detection settings."""
        self._ensure_working()
        assert self._working is not None
        if user_input is not None:
            power_enabled = user_input.get(CONF_POWER_SWITCH_ENABLED, False)
            power_switch = user_input.get(CONF_POWER_SWITCH)
            if power_enabled and power_switch and str(power_switch).strip():
                self._working[CONF_POWER_SWITCH_ENABLED] = True
                self._working[CONF_POWER_SWITCH] = str(power_switch).strip()
            else:
                # Disabled, or enabled without a valid entity -> clear the entity.
                self._working[CONF_POWER_SWITCH_ENABLED] = bool(power_enabled)
                self._working[CONF_POWER_SWITCH] = None
            return await self.async_step_init()

        current_power_switch_raw = self._working.get(CONF_POWER_SWITCH)
        current_power_enabled = self._working.get(CONF_POWER_SWITCH_ENABLED, False)
        # Migration: a stored switch without the enabled flag implies enabled.
        if current_power_switch_raw and CONF_POWER_SWITCH_ENABLED not in self._working:
            current_power_enabled = True

        current_power_switch = None
        if isinstance(current_power_switch_raw, str) and "." in current_power_switch_raw.strip():
            current_power_switch = current_power_switch_raw.strip()
        elif isinstance(current_power_switch_raw, list) and current_power_switch_raw:
            entity = current_power_switch_raw[0]
            if isinstance(entity, str) and "." in entity.strip():
                current_power_switch = entity.strip()

        schema_dict: dict[str, Any] = {
            vol.Optional(CONF_POWER_SWITCH_ENABLED, default=current_power_enabled): selector.BooleanSelector(),
            vol.Optional(
                CONF_POWER_SWITCH,
                default=(current_power_switch if current_power_switch else vol.UNDEFINED),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "input_boolean", "light"])
            ),
        }
        return self.async_show_form(
            step_id="power",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "power_help": "Optional power switch entity ID (e.g., switch.smart_plug_name) to enable accurate 'Off' state detection",
            },
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Connection (IP) and performance (polling) settings."""
        self._ensure_working()
        assert self._working is not None
        if user_input is not None:
            new_host = str(user_input.get(CONF_HOST) or "").strip()
            if new_host:
                self._working_host = new_host
            self._working[CONF_POLLING_RATE] = user_input.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
            return await self.async_step_init()

        schema_dict: dict[str, Any] = {
            vol.Optional(CONF_HOST, default=self._working_host or ""): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT, autocomplete="off")
            ),
            vol.Optional(
                CONF_POLLING_RATE,
                default=self._working.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=60, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="sec")
            ),
        }
        return self.async_show_form(step_id="connection", data_schema=vol.Schema(schema_dict))