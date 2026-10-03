import hashlib
import json
import logging
from pathlib import Path
from homeassistant.components.http import StaticPathConfig  # type: ignore[import]
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

LOCAL_SUBDIR = "ha_creality_ws"
PRINTER_CARD_NAME = "k_printer_card.js"
CFS_CARD_NAME = "k_cfs_card.js"
CARDS = [PRINTER_CARD_NAME, CFS_CARD_NAME]
# Static files the cards fetch at runtime. Listed explicitly, one registration
# each, rather than exposing the whole www/ directory -- that would also serve
# ha_creality_ws.code-workspace and change how the cards themselves are served
# as a side effect of adding an image.
ASSETS = ["cfs_box.webp"]
INTEGRATION_URL_BASE = f"/{LOCAL_SUBDIR}/"
# Static routes are per-process, not per-config-entry. See _register_static_path.
_STATIC_PATHS_KEY = f"{LOCAL_SUBDIR}_static_paths"
I18N_URL_BASE = f"{INTEGRATION_URL_BASE}i18n"
def card_version(card_name: str) -> str:
    """Cache-buster for one card, derived from what is actually being served.

    This used to be ``str(int(time.time()))``, evaluated once at import. That
    changed on every Home Assistant start, which meant two things: the Lovelace
    resource entry was rewritten on every restart whether or not the card had
    changed, and every browser threw away a good copy of the card each time.

    Hashing the file's own bytes instead makes the URL change exactly when the
    card changes -- which is the property an update needs. The manifest version
    is folded in because HACS restores files from a release archive and can
    preserve their timestamps, so nothing else in the path is guaranteed to
    move on an upgrade.

    Reads the file, so callers must keep this off the event loop.
    """
    base = Path(__file__).parent
    digest = hashlib.sha256()
    try:
        digest.update(
            json.loads((base / "manifest.json").read_text(encoding="utf-8"))["version"].encode()
        )
    except Exception:  # pylint: disable=broad-except
        # A missing or malformed manifest is not a reason to stop serving the
        # card; the file hash below is the part that actually has to be right.
        _LOGGER.debug("Could not read manifest version for the %s cache buster", card_name)
    try:
        digest.update((base / "www" / card_name).read_bytes())
    except OSError as exc:
        # No file to hash means the card is about to 404 anyway. Return a token
        # that is stable rather than random so the resource entry does not
        # churn while somebody fixes the install.
        _LOGGER.warning("Could not hash %s for its cache buster: %s", card_name, exc)
        return "missing"
    return digest.hexdigest()[:10]


def _register_static_path(
    hass: HomeAssistant, url_path: str, path: str, *, cache_headers: bool = True
) -> None:
    """Serve a file or directory straight out of the integration package.

    Deliberately served from the integration's own `www/` folder rather than
    copied into /config/www, so an update cannot leave a stale copy behind.

    Registration is done in a task with its own error handling: aiohttp raises
    when the same method and path are already registered, and an unretrieved
    task exception would otherwise surface as a noisy traceback in the log.

    Tracked per Home Assistant process, because `async_register_static_paths`
    does not deduplicate and this runs from `async_setup_entry`: a second
    printer, or any options change that reloads the entry, would otherwise
    re-register the same four paths and raise every time. That used to be
    accepted as the price of not being silent about a real failure, since both
    cases logged the same warning. Skipping the duplicate instead means the
    warning below now only ever means the real thing.

    The marker is dropped again if registration fails, so a genuine failure
    stays retryable on the next reload.
    """
    registered: set[str] = hass.data.setdefault(_STATIC_PATHS_KEY, set())
    if url_path in registered:
        return
    registered.add(url_path)

    async def _register() -> None:
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(url_path, path, cache_headers)]
            )
        except Exception as exc:  # pylint: disable=broad-except
            # Warning, not debug: if this fails the Lovelace cards 404 on every
            # dashboard, and at debug level nothing would say why.
            registered.discard(url_path)
            _LOGGER.warning(
                "Could not serve %s from %s: %s", url_path, path, exc
            )

    hass.async_create_task(_register())


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
        lovelace.resources
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
        lovelace.resources
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

    async def async_register(self) -> None:
        """Register a static path that serves the card from the integration package.

        We do NOT auto-create or modify Lovelace resources to avoid clobbering user
        dashboards. Instead we log the integration-hosted URL for manual registration.
        """
        versions: dict[str, str] = {}
        for card_name in CARDS:
            integration_url = f"{INTEGRATION_URL_BASE}{card_name}"
            serve_path = str(Path(__file__).parent / "www" / card_name)
            # Hashing reads the card off disk, so keep it out of the event loop.
            version = await self.hass.async_add_executor_job(card_version, card_name)
            versions[card_name] = version

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
                await _init_resource(self.hass, integration_url, version)
                _LOGGER.debug("Auto-registered lovelace resource for %s", integration_url)
            except Exception:
                _LOGGER.debug("Auto-registration of lovelace resource failed for %s", integration_url)

            # If there are existing lovelace resources that still point to /local/...,
            # migrate them to the integration-hosted URL to avoid leaving stale references.
            try:
                migrated = await _migrate_local_resources(
                    self.hass, f"/local/{LOCAL_SUBDIR}/{card_name}", integration_url, version
                )
                if migrated:
                    _LOGGER.info("Migrated %d Lovelace /local/ resources to integration-hosted URL", migrated)
            except Exception:
                _LOGGER.debug("Local-to-integration resource migration failed for %s", integration_url)

        for asset_name in ASSETS:
            asset_path = Path(__file__).parent / "www" / asset_name
            if asset_path.exists():
                _register_static_path(
                    self.hass,
                    f"{INTEGRATION_URL_BASE}{asset_name}",
                    str(asset_path),
                )
            else:
                _LOGGER.warning("Card asset missing, not registered: %s", asset_path)

        i18n_path = Path(__file__).parent / "www" / "i18n"
        if i18n_path.exists():
            # No cache headers here, unlike the cards. Their URLs carry a
            # `?v=` derived from the file's own bytes, so a month-long
            # max-age is exactly what you want; the i18n files are fetched
            # by bare path, so the same header would leave a browser on the
            # old translations until the cache expired.
            _register_static_path(
                self.hass, I18N_URL_BASE, str(i18n_path), cache_headers=False
            )

        # Fix any base-only resource entries (e.g. "/ha_creality_ws/?v=1") by expanding
        # them into the concrete card file URL(s).
        try:
            await _expand_base_resource(self.hass, INTEGRATION_URL_BASE, versions)
        except Exception:
            _LOGGER.debug("Failed to expand base resource entries for %s", LOCAL_SUBDIR)

        _LOGGER.info(
            "K cards served from integration at %s (type: module).",
            INTEGRATION_URL_BASE,
        )

async def _expand_base_resource(
    hass: HomeAssistant, base: str, card_versions: dict[str, str]
) -> int:
    """Expand any resources that point to `base` (with no filename) into per-card URLs.

    Takes the cache busters rather than computing them: hashing reads the cards
    off disk, and this runs on the event loop.

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
        lovelace.resources
    )

    await resources.async_get_info()

    created = 0

    # Build full target urls
    targets = [f"{base.rstrip('/')}/{name}?v={ver}" for name, ver in card_versions.items()]

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