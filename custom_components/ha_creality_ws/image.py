from __future__ import annotations
import logging
from typing import Any, Optional
from datetime import datetime
import base64
import time

from homeassistant.components.image import ImageEntity  # type: ignore[import]
from homeassistant.core import HomeAssistant  # type: ignore[import]
from homeassistant.config_entries import ConfigEntry  # type: ignore[import]
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore[import]
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # type: ignore[import]
import aiohttp  # type: ignore[import]

from .const import DOMAIN
from .entity import KEntity

_LOGGER = logging.getLogger(__name__)

# 1x1 transparent PNG as a lightweight placeholder (no logo to avoid copyright issues)
_PNG_PLACEHOLDER = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
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

    _attr_name = "Current Print Preview"
    _attr_content_type = "image/png"

    def __init__(self, coordinator):
        KEntity.__init__(self, coordinator, self._attr_name, "current_print_preview")
        ImageEntity.__init__(self, coordinator.hass)
        self._last_image: Optional[bytes] = None
        self._attr_image_last_updated = None
        self._last_reason: str | None = None
        self._last_source_url: str | None = None
        self._last_fetch_ts: float = 0.0
        self._min_fetch_interval: float = 5.0  # seconds

    def _status_allows_preview(self) -> bool:
        d = self.coordinator.data or {}
        if self._should_zero():
            return False
        st = d.get("state")
        fname = (d.get("printFileName") or "").strip()
        if not fname:
            return False
        prog = d.get("printProgress", d.get("dProgress"))
        try:
            prog = int(prog) if prog is not None else -1
        except Exception:
            prog = -1
        if prog >= 100:
            return True
        if d.get("withSelfTest"):
            return True
        return st == 1

    @property
    def available(self) -> bool:
        return True

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
                            self._last_image = data
                            self._last_source_url = url
                            self._attr_image_last_updated = datetime.utcnow()
                            self._last_reason = "ok"
                            self._last_fetch_ts = now
                            return data
            except Exception as exc:
                _LOGGER.debug("current_print_preview fetch failed for %s: %s", url, exc)

        self._last_reason = "fetch_failed"
        return self._last_image or _PNG_PLACEHOLDER
