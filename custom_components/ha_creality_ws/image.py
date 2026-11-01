from __future__ import annotations
import logging
from typing import Any
import base64
import time

from homeassistant.components.image import ImageEntity  # type: ignore[import]
from homeassistant.core import HomeAssistant, callback  # type: ignore[import]
from homeassistant.config_entries import ConfigEntry  # type: ignore[import]
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]
from homeassistant.util import dt as dt_util  # type: ignore[import]
import aiohttp  # type: ignore[import]

from .const import DOMAIN
from .utils import PREVIEW_PRINT_STATES, derive_activity_state
from .entity import KEntity

_LOGGER = logging.getLogger(__name__)

# 1x1 transparent PNG as a lightweight placeholder (no logo to avoid copyright issues)
_PNG_PLACEHOLDER = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    ent: list[ImageEntity] = []

    try:
        ent.append(CurrentPrintPreviewImage(coord))
    except Exception:
        _LOGGER.exception("Failed to initialize current print preview image entity")

    async_add_entities(ent)


class CurrentPrintPreviewImage(KEntity, ImageEntity):
    """Image entity for the G-code preview of the current print.

    This entity will attempt the printer-local preview URL used by K1 devices
    but will try the same path for any model. If the URL is unavailable the
    entity returns a small placeholder PNG and records the failure in
    `preview_reason`.
    """

    _attr_translation_key = "current_print_preview"
    _attr_content_type = "image/png"

    def __init__(self, coordinator):
        KEntity.__init__(self, coordinator, unique_id="current_print_preview")
        ImageEntity.__init__(self, coordinator.hass)
        self._last_image: bytes | None = None
        self._attr_image_last_updated = None
        self._last_reason: str | None = None
        self._last_source_url: str | None = None
        self._last_fetch_ts: float = 0.0
        self._min_fetch_interval: float = 5.0  # seconds
        self._last_job: tuple[str, Any] | None = None

    def _status_allows_preview(self) -> bool:
        """Whether there is a print whose preview is worth fetching.

        Routed through the shared state derivation rather than re-deriving the
        state/progress/withSelfTest combination locally, which was a third
        independent copy of the same mapping -- and one the notification layer
        depends on transitively, since it reads `preview_reason` to decide
        whether to attach the preview at all.

        `derive_activity_state` rather than `derive_print_state`, so a stale
        error code the printer never clears does not hide the preview for the
        rest of the print. Paused and processing jobs now qualify too: the model
        is still on the bed, and the old `state == 1` test made the preview
        vanish for the duration of a pause.
        """
        if self._should_zero():
            return False
        d = self.coordinator.data or {}
        if not (d.get("printFileName") or "").strip():
            return False
        return (
            derive_activity_state(d, paused_flag=self.coordinator._paused_flag)
            in PREVIEW_PRINT_STATES
        )

    @property
    def available(self) -> bool:
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Start each job from a clean slate.

        The timestamp only moved when bytes were fetched, so a dashboard kept
        the previous job's picture until the access token rotated, and the
        idle-time `preview_reason` of "not_printing" outlived the job start
        (R27). A new job drops both, and the new timestamp makes the frontend
        fetch this job's preview straight away. A reprint of the same file is a
        new job too, sliced again maybe, and printers that date their jobs give
        it a new `printStartTime` (R98); without one, it kept the last version,
        so a notification could carry a picture iOS had cached for it (#131).
        """
        d = self.coordinator.data or {}
        name = (d.get("printFileName") or "").strip()
        job = (name, d.get("printStartTime"))
        if name and job != self._last_job:
            if self._last_job is not None:
                self._last_image = None
                self._last_reason = None
                self._last_source_url = None
                self._last_fetch_ts = 0.0
                self._attr_image_last_updated = dt_util.utcnow()
            self._last_job = job
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return {
            "preview_reason": self._last_reason,
            "source_url": self._last_source_url,
        }

    async def async_image(self) -> bytes | None:
        if not self._status_allows_preview():
            self._last_reason = "not_printing"
            self._last_source_url = None
            return self._last_image or _PNG_PLACEHOLDER

        # Attempt the standard preview URLs for any model. Some printers may
        # expose the same path even when not K1-family devices. Fall back to
        # placeholder when unavailable.

        now = time.monotonic()
        if self._last_image is not None and (now - self._last_fetch_ts) < self._min_fetch_interval:
            return self._last_image

        host = self._host
        candidates = [
            f"https://{host}/downloads/original/current_print_image.png",
            f"http://{host}/downloads/original/current_print_image.png",
        ]

        # Ensure diagnostics URL cache exists
        try:
            urls = getattr(self.coordinator, "_http_urls_accessed", None)
            if urls is None:
                urls = set()
                setattr(self.coordinator, "_http_urls_accessed", urls)
        except Exception:
            urls = None

        session = async_get_clientsession(self.coordinator.hass)
        for url in candidates:
            try:
                if urls is not None:
                    urls.add(url)
            except Exception:
                # Ignore errors when updating diagnostics URL cache; non-critical.
                pass
            try:
                ssl_opt = False if url.startswith("https://") else None
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=ssl_opt) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        if data:
                            # Only a different picture is a new one. The state is
                            # this timestamp, and notifications version their
                            # preview URL by it (#131): moving it on every fetch
                            # re-keyed the URL each time a phone downloaded it.
                            if data != self._last_image:
                                self._attr_image_last_updated = dt_util.utcnow()
                            self._last_image = data
                            self._last_source_url = url
                            self._last_reason = "ok"
                            self._last_fetch_ts = now
                            return data
            except Exception as exc:
                _LOGGER.debug("current_print_preview fetch failed for %s: %s", url, exc)

        self._last_reason = "fetch_failed"
        return self._last_image or _PNG_PLACEHOLDER
