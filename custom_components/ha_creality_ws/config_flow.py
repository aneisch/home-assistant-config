from __future__ import annotations
import asyncio
import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse
from .notification_rules import (
    TEMPLATE_FIELDS,
    coerce_targets,
    template_unknown_fields,
)
import voluptuous as vol
from homeassistant import config_entries #type: ignore[import]
from homeassistant.config_entries import ConfigFlowResult #type: ignore[import]
from homeassistant.data_entry_flow import section #type: ignore[import]
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
    CONF_GO2RTC_RTSP_PORT,
    GO2RTC_SOURCE_SCHEMES,
    CONF_CUSTOM_CAMERA_URL,
    DEFAULT_GO2RTC_URL,
    DEFAULT_GO2RTC_PORT,
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
    CONF_POLLING_RATE,
    DEFAULT_POLLING_RATE,
    NOTIFY_TEMPLATE_OPTIONS,
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
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        # The entry is deliberately not passed on: OptionsFlow.config_entry is
        # a property Home Assistant resolves itself, so handing it over again
        # only created a second reference to keep in step.
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_zeroconf(self, discovery_info: Any) -> ConfigFlowResult:
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


# The collapsible groups on the notifications page, and what each field falls
# back to. One map, read three times: it is what the form renders defaults from,
# what decides whether a group opens folded, and what a submitted section is
# flattened against. Three copies of the same defaults is how a checkbox ends up
# rendering as off while the code treats it as on.
SECTION_EVENTS = "events"
SECTION_EXTRAS = "extras"
SECTION_TEXT = "text"

_NOTIFY_SECTIONS: dict[str, dict[str, Any]] = {
    SECTION_EVENTS: {
        CONF_NOTIFY_LIVE: False,
        CONF_NOTIFY_COMPLETED: False,
        CONF_NOTIFY_ERROR: False,
        CONF_NOTIFY_MINUTES_TO_END: False,
        CONF_MINUTES_TO_END_VALUE: 5,
    },
    SECTION_EXTRAS: {
        CONF_NOTIFY_ACTIONS: False,
        CONF_NOTIFY_PREVIEW_IMAGE: True,
        CONF_NOTIFY_CAMERA_SNAPSHOT: True,
        CONF_NOTIFY_TAP_PATH: "",
    },
    SECTION_TEXT: {key: "" for key in NOTIFY_TEMPLATE_OPTIONS.values()},
}

_NOTIFY_DEFAULTS: dict[str, Any] = {
    key: default
    for fields in _NOTIFY_SECTIONS.values()
    for key, default in fields.items()
}


def _flatten_sections(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """One flat dict from a submit whose fields live in sections.

    A section arrives as a nested dict under its own name. Everything past this
    point -- validation, the working copy, the options in `.storage` -- is flat,
    and deliberately so: the grouping is a property of the form, not of the
    settings, so moving a field between groups must not move it in a user's
    config or orphan what they already saved.
    """
    flat: dict[str, Any] = {}
    for key, value in user_input.items():
        if key in _NOTIFY_SECTIONS and isinstance(value, Mapping):
            flat.update(value)
        else:
            flat[key] = value
    return flat


def _placeholder_help(name: str) -> str:
    """The placeholders one notification can fill, as a comma-separated line.

    Per notification, because they are not all the same: the finishing-soon
    reminder is the only one that knows how many minutes are left, and a print
    that has been stopped has had most of its numbers reset by the printer
    before anything can read them. Offering a placeholder that cannot be filled
    is worse than not offering it -- it renders as nothing, which reads as a bug
    in the user's template rather than a mistake in the list.

    Generated from the single source of truth in `notification_rules`, so a new
    placeholder documents itself in the UI, in every language, without six
    near-identical lists to keep in step. Not prose: the surrounding sentence
    lives in strings.json and is translated; these are the names the user has to
    type.

    Fed in as a `description_placeholders` value rather than written into the
    sentence, and so is the example below. The frontend renders a step
    description through ICU MessageFormat, where a `{name}` it was given no
    value for is an error that replaces the entire description with
    "Translation error" -- so the one place a brace may appear literally in
    strings.json is inside a value substituted into it.
    """
    return ", ".join(f"{{{field}}}" for field in TEMPLATE_FIELDS[name])


def _placeholder_example() -> str:
    """A template showing the optional-segment syntax, in no language at all.

    Punctuation only, deliberately: an example reading "4h left" would need
    translating, and it arrives through `description_placeholders`, which is not
    translated. The syntax is the whole lesson here anyway.
    """
    return "{filename} {progress}%[ - {eta}]"


# --------- Options Flow ---------
class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self) -> None:
        super().__init__()
        # The options as this dialog has them, rebuilt from the entry the first
        # time a step runs. Each section's submit folds its fields in here and
        # then writes the whole thing to the entry, so a section is saved the
        # moment it is submitted.
        #
        # This used to be a staging buffer that only "Save and apply" persisted,
        # and the menu offered no hint that it was the one item you could not
        # skip: closing the dialog -- which is how a settings dialog normally
        # ends -- silently discarded everything. None until first use.
        self._working: dict[str, Any] | None = None
        self._working_host: str | None = None

    def _ensure_working(self) -> None:
        """Initialize the working copy once per options-flow session."""
        if self._working is None:
            self._working = dict(self.config_entry.options)
            self._working_host = self.config_entry.data.get(CONF_HOST, "")

    def _persist(self) -> None:
        """Write the working copy to the config entry, now.

        Called by every section's submit. The update listener reloads the entry,
        which is what applies the change -- so one submit is one reload, and a
        section the user never opened cannot be rewritten by one they did.

        A host change goes out in the *same* call as the options: it lives in
        `data` rather than `options`, and updating the two separately fired the
        listener twice and reloaded the entry twice for one submit.

        Home Assistant compares before it writes, so re-submitting a section
        unchanged is not an update and does not reload anything.
        """
        assert self._working is not None
        updates: dict[str, Any] = {"options": dict(self._working)}
        if self._working_host and self._working_host != self.config_entry.data.get(CONF_HOST):
            updates["data"] = {**self.config_entry.data, CONF_HOST: self._working_host}
        self.hass.config_entries.async_update_entry(self.config_entry, **updates)

    async def _saved(self) -> ConfigFlowResult:
        """Persist the section just submitted and go back to the menu."""
        self._persist()
        return await self.async_step_init()

    async def _detect_camera_type(self) -> str:
        """Detect the camera type for this printer."""
        host = self.config_entry.data["host"]
        
        # Get the coordinator to access printer data
        try:
            coord = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
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

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Top-level options menu (the hub each section returns to).

        Each settings group is its own step so its form is rebuilt fresh from the
        working copy every time it is opened -- Home Assistant cannot re-render a
        single step when a dropdown changes, so conditional fields (e.g. the
        custom camera URL) would otherwise show stale based on the saved mode.

        Submitting a page saves it, and there is deliberately nothing here to
        press afterwards: the way out is the dialog's own close button, like
        every other dialog in Home Assistant, and it cannot lose anything.
        A "Save and apply" item used to sit at the bottom of this menu, which
        made the one thing you could not skip look like one more thing you
        could -- closing the dialog, which is how a settings dialog normally
        ends, silently threw the lot away.

        A list rather than a mapping, so the labels come from `menu_options` in
        strings.json and are translated. Passing a mapping makes the frontend
        render its values verbatim, which left every locale reading English.
        """
        self._ensure_working()
        return self.async_show_menu(
            step_id="init",
            menu_options=["camera", "notifications", "power", "connection"],
        )

    async def async_step_camera(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Camera settings. Conditional fields follow the selected mode."""
        self._ensure_working()
        assert self._working is not None
        errors: dict[str, str] = {}
        # Camera fields are staged into a copy and only folded into the working
        # options once the whole page validates.
        staged = dict(self._working)
        saved_mode = self._working.get(CONF_CAMERA_MODE, CAM_MODE_AUTO)
        # Mode to render fields for: the just-submitted one (so the error re-render
        # reveals the right fields), otherwise the staged/saved one.
        effective_mode = (user_input or {}).get(CONF_CAMERA_MODE, saved_mode)

        if user_input is not None:
            camera_mode = user_input.get(CONF_CAMERA_MODE, CAM_MODE_AUTO)
            if camera_mode == CAM_MODE_AUTO:
                camera_mode = await self._detect_camera_type()
                _LOGGER.info("ha_creality_ws: auto mode detected camera type: %s", camera_mode)

            staged[CONF_CAMERA_MODE] = camera_mode

            if camera_mode == CAM_MODE_CUSTOM:
                custom_url = str(user_input.get(CONF_CUSTOM_CAMERA_URL) or "").strip()
                parsed = urlparse(custom_url)
                # Require a supported scheme and a host. http(s) -> MJPEG/snapshot;
                # rtsp/rtmp/srt -> ingested via go2rtc (see camera.async_setup_entry).
                #
                # `hostname` and not `netloc`: "rtsp://user@" has a non-empty
                # netloc made entirely of userinfo, so it passed validation and
                # was saved as a source nothing can connect to.
                if parsed.scheme.lower() not in ("http", "https") + GO2RTC_SOURCE_SCHEMES or not parsed.hostname:
                    errors[CONF_CUSTOM_CAMERA_URL] = "invalid_camera_url"
                    effective_mode = CAM_MODE_CUSTOM  # ensure the URL field is shown
                else:
                    staged[CONF_CUSTOM_CAMERA_URL] = custom_url

            # A Custom source with an rtsp/rtmp/srt URL is ingested by go2rtc as
            # well (camera.async_setup_entry -> _make_go2rtc_camera), so it needs
            # the same settings. Popping them left that path unable to reach an
            # external go2rtc at all, and silently dropped its RTSP port.
            custom_uses_go2rtc = (
                camera_mode == CAM_MODE_CUSTOM
                and urlparse(staged.get(CONF_CUSTOM_CAMERA_URL, "") or "")
                    .scheme.lower() in GO2RTC_SOURCE_SCHEMES
            )

            if camera_mode == CAM_MODE_WEBRTC or custom_uses_go2rtc:
                # Only fields the form actually rendered are applied. A submit can
                # reach here without them: switching to Custom hides the go2rtc
                # fields, and the Custom-uses-go2rtc branch then ran with no
                # go2rtc keys in user_input, so `.get() or DEFAULT` silently
                # replaced a configured external server with localhost:11984.
                if CONF_GO2RTC_URL in user_input:
                    staged[CONF_GO2RTC_URL] = (
                        str(user_input.get(CONF_GO2RTC_URL) or "").strip() or DEFAULT_GO2RTC_URL
                    )
                elif CONF_GO2RTC_URL not in staged:
                    staged[CONF_GO2RTC_URL] = DEFAULT_GO2RTC_URL

                if CONF_GO2RTC_PORT in user_input:
                    port = user_input.get(CONF_GO2RTC_PORT)
                    try:
                        staged[CONF_GO2RTC_PORT] = int(port) if port is not None else DEFAULT_GO2RTC_PORT
                    except (ValueError, TypeError):
                        staged[CONF_GO2RTC_PORT] = DEFAULT_GO2RTC_PORT
                elif CONF_GO2RTC_PORT not in staged:
                    staged[CONF_GO2RTC_PORT] = DEFAULT_GO2RTC_PORT

                # RTSP port is only needed for HA's HLS pipeline; blank/0 means
                # "auto-detect" (18554 for HA-managed go2rtc, 8554 otherwise).
                if CONF_GO2RTC_RTSP_PORT in user_input:
                    rtsp_port = user_input.get(CONF_GO2RTC_RTSP_PORT)
                    try:
                        rtsp_port_int = int(rtsp_port) if rtsp_port is not None else 0
                    except (ValueError, TypeError):
                        rtsp_port_int = 0
                    if rtsp_port_int > 0:
                        staged[CONF_GO2RTC_RTSP_PORT] = rtsp_port_int
                    else:
                        staged.pop(CONF_GO2RTC_RTSP_PORT, None)
            elif not errors:
                # Drop go2rtc settings for non-go2rtc modes so they don't linger.
                # Only once the submission is otherwise valid: an invalid Custom
                # URL re-renders this step, and discarding the settings meanwhile
                # lost them before the user could correct the URL.
                staged.pop(CONF_GO2RTC_URL, None)
                staged.pop(CONF_GO2RTC_PORT, None)
                staged.pop(CONF_GO2RTC_RTSP_PORT, None)

            if not errors:
                # Folded in only here. `_persist` writes the whole dict, so a
                # field applied by a submit that was then rejected would be
                # saved by whichever section the user submits next -- a Custom
                # mode with no URL to go with it. The notifications step stages
                # its own fields for the same reason.
                self._working = staged
                return await self._saved()

        current_go2rtc_url = staged.get(CONF_GO2RTC_URL, DEFAULT_GO2RTC_URL)
        current_go2rtc_port = staged.get(CONF_GO2RTC_PORT, DEFAULT_GO2RTC_PORT)
        # 0 renders as "auto-detect" in the form.
        current_go2rtc_rtsp_port = staged.get(CONF_GO2RTC_RTSP_PORT, 0)
        current_custom_url = staged.get(CONF_CUSTOM_CAMERA_URL, "")
        # Offered for Custom too once its URL is a go2rtc-ingested scheme, since
        # that path builds a go2rtc camera. On a fresh Custom setup the URL is not
        # staged yet, so the fields appear the next time the step is opened.
        show_go2rtc = effective_mode in (CAM_MODE_WEBRTC, CAM_MODE_AUTO) or (
            effective_mode == CAM_MODE_CUSTOM
            and urlparse(current_custom_url or "").scheme.lower() in GO2RTC_SOURCE_SCHEMES
        )
        show_custom_url = effective_mode == CAM_MODE_CUSTOM

        schema_dict: dict[str, Any] = {
            vol.Optional(CONF_CAMERA_MODE, default=effective_mode): selector.SelectSelector(
                # Bare values plus a translation_key: the visible labels live
                # under `selector.camera_mode.options` in strings.json, so they
                # are translated like everything else rather than hardcoded here.
                selector.SelectSelectorConfig(
                    options=[
                        CAM_MODE_AUTO,
                        CAM_MODE_MJPEG,
                        CAM_MODE_WEBRTC,
                        CAM_MODE_WEBRTC_DIRECT,
                        CAM_MODE_CUSTOM,
                    ],
                    translation_key="camera_mode",
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
                vol.Optional(CONF_GO2RTC_RTSP_PORT, default=current_go2rtc_rtsp_port): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=65535, mode=selector.NumberSelectorMode.BOX)
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
        )

    def _notify_target_options(self, current: list[str]) -> list[Any]:
        """Every notify target we can offer, plus whatever is already stored.

        Covers both dialects: legacy `notify.<service>` services and modern
        notify *entities*. Anything already configured is kept in the list even
        if its integration is not loaded right now, so opening this step while a
        phone's integration is down does not quietly drop it on save.
        """
        # `send_message` is the generic action for notify *entities*: it takes an
        # `entity_id`, so offering it as a destination gives the user a target
        # that dispatch can only fail on. The entities themselves come from
        # `async_entity_ids` below, which is the form that works.
        candidates: list[str] = [
            f"notify.{name}"
            for name in self.hass.services.async_services().get("notify", {})
            if name != "send_message"
        ]
        try:
            candidates.extend(self.hass.states.async_entity_ids("notify"))
        except Exception:  # pylint: disable=broad-except
            # A stub in tests, where states is not backed by a registry.
            # The service list alone is enough to render the step.
            pass
        candidates.extend(current)
        return [
            selector.SelectOptionDict(value=value, label=value)
            for value in sorted(set(candidates))
        ]

    async def async_step_notifications(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Everything about notifications, on one page.

        Targets first, because nothing else on the page does anything without
        one, then three collapsible groups. It used to be two separate pages
        with ten fields in a flat list between them, which meant the custom text
        for a notification was nowhere near the switch that turns it on.

        A group the user has changed something in opens by itself, so a printer
        with custom wording shows it rather than hiding it behind a disclosure
        that looks untouched. So does a group holding an error.
        """
        self._ensure_working()
        assert self._working is not None
        errors: dict[str, str] = {}
        submitted = _flatten_sections(user_input) if user_input is not None else {}

        if user_input is not None:
            # Never persist None. `options.get(key, DEFAULT)` returns the stored
            # None rather than the default, and the int()/float() casts at setup
            # then fail for good -- a cleared field would brick the entry.
            cleaned = {k: v for k, v in submitted.items() if v is not None}
            if CONF_NOTIFY_TARGETS in submitted:
                cleaned[CONF_NOTIFY_TARGETS] = [
                    t.strip()
                    for t in (cleaned.get(CONF_NOTIFY_TARGETS) or [])
                    if isinstance(t, str) and t.strip()
                ]
            for name, key in NOTIFY_TEMPLATE_OPTIONS.items():
                # Only what the submit actually carried. Every field of a group
                # comes back whether or not it was unfolded, but a group the
                # form did not render at all must keep what is stored -- reading
                # an absent field as "the user cleared it" would wipe all six
                # templates the first time anything submitted without them.
                if key not in submitted:
                    continue
                text = str(submitted.get(key) or "").strip()
                # Against the placeholders *this* notification can fill. A
                # `{minutes}` in the live card is not a typo anywhere else, and
                # at run time it would simply have rendered as nothing.
                if template_unknown_fields(text, TEMPLATE_FIELDS[name]):
                    errors[key] = "unknown_placeholder"
                else:
                    cleaned[key] = text
            if not errors:
                # Applied only once the whole page is valid, so a refused submit
                # leaves the stored options exactly as they were rather than
                # saving the good half of a page the user is still correcting.
                self._working.update(cleaned)
                return await self._saved()

        def stored(key: str) -> Any:
            """The value to render: what was just submitted, else what is saved.

            The rejected text and not the stored one: a re-render that replaced
            what the user typed with what was saved would take their typo away
            along with any chance of fixing it.
            """
            default = _NOTIFY_DEFAULTS[key]
            if user_input is not None:
                return submitted.get(key, default)
            value = self._working.get(key)
            return default if value is None else value

        # Seeded through the same coercion the coordinator uses, so a user
        # upgrading from the single-device option sees it pre-selected here and
        # the first save persists the new shape.
        current_targets = (
            submitted.get(CONF_NOTIFY_TARGETS)
            if user_input is not None
            else coerce_targets(self._working)
        ) or []

        events = {
            vol.Optional(CONF_NOTIFY_LIVE, default=stored(CONF_NOTIFY_LIVE)):
                selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_COMPLETED, default=stored(CONF_NOTIFY_COMPLETED)
            ): selector.BooleanSelector(),
            vol.Optional(CONF_NOTIFY_ERROR, default=stored(CONF_NOTIFY_ERROR)):
                selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_MINUTES_TO_END,
                default=stored(CONF_NOTIFY_MINUTES_TO_END),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MINUTES_TO_END_VALUE, default=stored(CONF_MINUTES_TO_END_VALUE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=60, mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
        }

        extras = {
            vol.Optional(
                CONF_NOTIFY_ACTIONS, default=stored(CONF_NOTIFY_ACTIONS)
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_PREVIEW_IMAGE,
                default=stored(CONF_NOTIFY_PREVIEW_IMAGE),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_CAMERA_SNAPSHOT,
                default=stored(CONF_NOTIFY_CAMERA_SNAPSHOT),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_TAP_PATH, default=stored(CONF_NOTIFY_TAP_PATH)
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT, autocomplete="off"
                )
            ),
        }

        text = {
            vol.Optional(key, default=stored(key)): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    autocomplete="off",
                    multiline=True,
                )
            )
            for key in NOTIFY_TEMPLATE_OPTIONS.values()
        }

        schema = vol.Schema({
            vol.Optional(CONF_NOTIFY_TARGETS, default=current_targets):
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._notify_target_options(current_targets),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=True,
                        custom_value=True,
                    )
                ),
            # Optional, as core's own sectioned flows have them: a submit that
            # arrives without one of these should leave those settings alone,
            # not fail the whole page on a schema error the user cannot read.
            # `_flatten_sections` writes back only what was actually submitted.
            vol.Optional(SECTION_EVENTS): section(
                vol.Schema(events), {"collapsed": False}
            ),
            vol.Optional(SECTION_EXTRAS): section(
                vol.Schema(extras),
                {"collapsed": not self._section_touched(SECTION_EXTRAS, errors)},
            ),
            vol.Optional(SECTION_TEXT): section(
                vol.Schema(text),
                {"collapsed": not self._section_touched(SECTION_TEXT, errors)},
            ),
        })

        # The placeholder lists are built here and passed in, so each field can
        # name the ones *it* accepts without strings.json having to be edited
        # whenever one is added, and without six near-identical lists drifting
        # apart in every locale.
        placeholders = {
            f"fields_{name}": _placeholder_help(name)
            for name in NOTIFY_TEMPLATE_OPTIONS
        }
        placeholders["example"] = _placeholder_example()
        return self.async_show_form(
            step_id="notifications",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    def _section_touched(self, name: str, errors: Mapping[str, str]) -> bool:
        """Whether a collapsible group holds anything worth opening it for.

        A group the user has changed, or one being pointed at by an error.
        Everything still at its default stays folded away, which is the whole
        point of putting it in a section.
        """
        assert self._working is not None
        keys = _NOTIFY_SECTIONS[name]
        if any(key in errors for key in keys):
            return True
        return any(
            key in self._working and self._working[key] != default
            for key, default in keys.items()
        )

    async def async_step_power(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
            return await self._saved()

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
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Connection (IP) and performance (polling) settings."""
        self._ensure_working()
        assert self._working is not None
        if user_input is not None:
            new_host = str(user_input.get(CONF_HOST) or "").strip()
            if new_host:
                self._working_host = new_host
            self._working[CONF_POLLING_RATE] = user_input.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
            return await self._saved()

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