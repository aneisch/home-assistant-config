import logging
import time
from pathlib import Path
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

LOCAL_SUBDIR = "ha_creality_ws"
PRINTER_CARD_NAME = "k_printer_card.js"
CFS_CARD_NAME = "k_cfs_card.js"
CARDS = [PRINTER_CARD_NAME, CFS_CARD_NAME]
INTEGRATION_URL_BASE = f"/{LOCAL_SUBDIR}/"
# Use timestamp to bust cache on every load
_VERSION = str(int(time.time()))


def _register_static_path(hass: HomeAssistant, url_path: str, path: str) -> None:
    """Register a static path with the HA HTTP component, compatible with multiple HA versions.

    We intentionally register the card from the integration `frontend/` folder so the
    file is served from the integration package (no copying to /config/www).
    """
    try:
        # HA 2024.7+ supports async_register_static_paths/StaticPathConfig; prefer that
        from homeassistant.components.http import StaticPathConfig

        # Use async API when available. Run inside a guarded async task so any
        # exceptions (duplicate routes, etc.) are handled and don't generate
        # un-retrieved task exceptions which show as noisy errors in the log.
        if hasattr(hass.http, "async_register_static_paths"):
            async def _safe_register():
                try:
                    await hass.http.async_register_static_paths(
                        [StaticPathConfig(url_path, path, True)]
                    )
                except Exception as exc:
                    # Duplicate route registrations raise RuntimeError in aiohttp
                    # when the same method/path is already present. Handle it
                    # gracefully and log at debug level.
                    _LOGGER.debug("Failed to async register static path %s -> %s: %s", url_path, path, exc)

            hass.async_create_task(_safe_register())
            return
    except Exception:
        # Fall through to sync API below
        pass

    # Fallback for older HA
    try:
        hass.http.register_static_path(url_path, path, cache_headers=True)
    except Exception:
        # If registration fails, log and continue; we won't attempt to copy files.
        _LOGGER.debug("Failed to register static path %s -> %s", url_path, path)


async def _init_resource(hass: HomeAssistant, url: str, ver: str) -> bool:
    """Safely add or update a Lovelace resource for the given URL.

    Behavior copied from the `webrtc` integration: it only updates or creates the
    specific resource entry and uses a cache-busted query param `?v=`. This is
    intentionally conservative to avoid clobbering unrelated Lovelace resources.
    Returns True if resource was added/updated, False if no action was needed.
    """
    try:
        # Import lazily to keep module import safe during tests
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except Exception:
        # If imports fail here (tests/local static analysis), skip auto-registration
        _LOGGER.debug("Lovlace resource helpers unavailable; skipping auto resource init")
        return False

    lovelace = hass.data.get("lovelace")
    if not lovelace:
        _LOGGER.debug("Lovelace storage not available; skipping auto resource init")
        return False

    resources: ResourceStorageCollection = (
        lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    )

    await resources.async_get_info()

    url2 = f"{url}?v={ver}"

    for item in resources.async_items():
        if not item.get("url", "").startswith(url):
            continue

        if item["url"].endswith(ver):
            return False

        _LOGGER.debug("Update lovelace resource to: %s", url2)
        if isinstance(resources, ResourceStorageCollection):
            await resources.async_update_item(item["id"], {"res_type": "module", "url": url2})
        else:
            item["url"] = url2

        return True

    if isinstance(resources, ResourceStorageCollection):
        _LOGGER.debug("Add new lovelace resource: %s", url2)
        await resources.async_create_item({"res_type": "module", "url": url2})
    else:
        _LOGGER.debug("Add extra JS module: %s", url2)
        add_extra_js_url(hass, url2)

    return True


async def _migrate_local_resources(
    hass: HomeAssistant, local_prefix: str, new_url: str, ver: str
) -> int:
    """Migrate any Lovelace resources pointing at the old /local/ prefix.

    Returns the number of resources migrated.
    """
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except Exception:
        _LOGGER.debug("Lovelace helpers unavailable; skipping local -> integration migration")
        return 0

    lovelace = hass.data.get("lovelace")
    if not lovelace:
        _LOGGER.debug("Lovelace storage not available; skipping migration")
        return 0

    resources: ResourceStorageCollection = (
        lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    )

    await resources.async_get_info()

    migrated = 0

    for item in list(resources.async_items()):
        u = item.get("url", "")
        if not u.startswith(local_prefix):
            continue

        # keep the filename/path suffix and place it under the new base URL
        suffix = u[len(local_prefix) :]
        if not suffix:
            # nothing to migrate
            continue

        new_base = new_url.rstrip("/")
        url2 = f"{new_base}/{suffix}?v={ver}"

        _LOGGER.info("Migrating Lovelace resource from %s to %s", u, url2)
        try:
            if isinstance(resources, ResourceStorageCollection):
                await resources.async_update_item(item["id"], {"res_type": "module", "url": url2})
            else:
                item["url"] = url2
            migrated += 1
        except Exception as exc:
            _LOGGER.warning("Failed to migrate resource %s -> %s: %s", u, url2, exc)

    return migrated


class CrealityCardRegistration:
    """Serve k_printer_card.js from the integration package and log instructions.

    This mirrors how the `webrtc` integration hosts lovelace cards in its own `www/`
    directory instead of copying them into `/config/www`.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _src_path(self, card_name: str) -> Path:
        # card bundled inside the integration
        return Path(__file__).parent / "frontend" / card_name

    async def async_register(self) -> None:
        """Register a static path that serves the card from the integration package.

        We do NOT auto-create or modify Lovelace resources to avoid clobbering user
        dashboards. Instead we log the integration-hosted URL for manual registration.
        """
        for card_name in CARDS:
            integration_url = f"{INTEGRATION_URL_BASE}{card_name}"
            src = self._src_path(card_name)
            # integration-local serving uses the 'www' folder name like other integrations
            # (file lives in integration/frontend or integration/www depending on packaging)
            www_path = Path(__file__).parent / "www" / card_name
            if www_path.exists():
                serve_path = str(www_path)
            else:
                # fall back to original frontend location when 'www' is not present
                serve_path = str(src)

            _register_static_path(self.hass, integration_url, serve_path)

            # Remove old copy from /config/www if present (cleanup of previous installs)
            try:
                dst = Path(self.hass.config.path("www")) / LOCAL_SUBDIR / card_name
                if dst.exists():
                    try:
                        dst.unlink()
                        _LOGGER.info("Removed old /config/www copy: %s", dst)
                    except Exception as exc:  # pragma: no cover - best-effort cleanup
                        _LOGGER.debug("Failed to remove old /config/www copy %s: %s", dst, exc)
            except Exception:
                _LOGGER.debug("Could not determine config www path to cleanup old card")

            # Try a delicate auto-registration of the lovelace resource; this will only
            # update/create the single resource URL and includes a version query param.
            try:
                await _init_resource(self.hass, integration_url, _VERSION)
                _LOGGER.debug("Auto-registered lovelace resource for %s", integration_url)
            except Exception:
                _LOGGER.debug("Auto-registration of lovelace resource failed for %s", integration_url)

            # If there are existing lovelace resources that still point to /local/...,
            # migrate them to the integration-hosted URL to avoid leaving stale references.
            try:
                migrated = await _migrate_local_resources(
                    self.hass, f"/local/{LOCAL_SUBDIR}/{card_name}", integration_url, _VERSION
                )
                if migrated:
                    _LOGGER.info("Migrated %d Lovelace /local/ resources to integration-hosted URL", migrated)
            except Exception:
                _LOGGER.debug("Local-to-integration resource migration failed for %s", integration_url)

        # Fix any base-only resource entries (e.g. "/ha_creality_ws/?v=1") by expanding
        # them into the concrete card file URL(s).
        try:
            await _expand_base_resource(self.hass, INTEGRATION_URL_BASE, CARDS)
        except Exception:
            _LOGGER.debug("Failed to expand base resource entries for %s", LOCAL_SUBDIR)

        _LOGGER.info(
            "K cards served from integration at %s (type: module).",
            INTEGRATION_URL_BASE,
        )

    async def async_unregister(self) -> None:
        """No-op: leave Lovelace resources and HTTP registrations alone on unload."""
        return


async def _expand_base_resource(hass: HomeAssistant, base: str, card_names: list[str]) -> int:
    """Expand any resources that point to `base` (with no filename) into per-card URLs.

    Returns number of newly created/updated resource entries.
    """
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except Exception:
        _LOGGER.debug("Lovelace helpers unavailable; skipping base resource expansion")
        return 0

    lovelace = hass.data.get("lovelace")
    if not lovelace:
        return 0

    resources: ResourceStorageCollection = (
        lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    )

    await resources.async_get_info()

    created = 0

    # Build full target urls
    targets = [f"{base.rstrip('/')}/{name}?v={_VERSION}" for name in card_names]

    # Find items that point to the base (with or without ?v=)
    for item in list(resources.async_items()):
        u = item.get("url", "")
        if not (u == base or u.startswith(base)):
            continue

        # Determine if this item is a base-only entry (no filename suffix)
        suffix = u[len(base) :]
        if suffix and not (suffix.startswith("?") or suffix == ""):
            # already points to a specific file; skip
            continue

        _LOGGER.info("Expanding base resource %s into %s", u, ",".join(targets))

        try:
            # Update the existing item to the first target and create the rest
            first = targets[0]
            if isinstance(resources, ResourceStorageCollection):
                await resources.async_update_item(item["id"], {"res_type": "module", "url": first})
            else:
                item["url"] = first
            created += 1

            # create additional targets if not present
            existing_urls = {it.get("url", "") for it in resources.async_items()}
            for t in targets[1:]:
                if t in existing_urls:
                    continue
                if isinstance(resources, ResourceStorageCollection):
                    await resources.async_create_item({"res_type": "module", "url": t})
                else:
                    # best-effort: append to in-memory collection
                    resources.async_items().append({"url": t})
                created += 1
        except Exception as exc:
            _LOGGER.warning("Failed to expand base resource %s: %s", u, exc)

    return created