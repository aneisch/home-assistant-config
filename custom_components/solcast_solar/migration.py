"""Schema migration, legacy key sync, and cache cleanup helpers."""

from pathlib import Path
from typing import Any

from .const import (
    API_LIMIT,
    AUTO_UPDATED,
    CUSTOM_HOURS,
    FAILURE,
    FORECASTS,
    INTEGRATION_VERSION,
    LAST_7D,
    LAST_14D,
    LAST_24H,
    LAST_ATTEMPT,
    LAST_UPDATED,
    SITE_INFO,
    SUCCESS,
    SUCCESS_FORCED,
    SUCCESS_TRACKED,
    VERSION,
)
from .log import get_logger

_LOGGER = get_logger(__name__)


def sync_legacy_keys(data: dict[str, Any]) -> None:
    """Keep legacy option key names in sync with their renamed counterparts.

    Maintains "api_quota" and "customhoursensor" alongside the current
    API_LIMIT and CUSTOM_HOURS keys so that a downgrade to a version
    predating their rename can still read the stored values.
    """
    if "api_quota" in data:
        data["api_quota"] = data[API_LIMIT]
    if "customhoursensor" in data:
        data["customhoursensor"] = data[CUSTOM_HOURS]


async def clear_cache(filename: str, warn: bool = True):
    """Deletes filename if it exists."""
    if Path(filename).is_file():
        Path(filename).unlink()
        _LOGGER.debug("Deleted cache file %s", Path(filename).name)
    elif warn:
        _LOGGER.warning("There is no %s to delete", Path(filename).name)


class SchemaIncompatibleError(Exception):
    """Raised when cache data cannot be upgraded due to incompatible structure."""


def upgrade_cache_schema(
    data: dict[str, Any],
    from_version: int,
    first_site_id: str | None,
    auto_update_enabled: bool,
) -> int:
    """Upgrade a cache data dict from *from_version* to the current JSON_VERSION.

    The dict is mutated in-place. Returns the version after upgrade.

    Raises:
        SchemaIncompatibleError: If the data structure is incompatible and
            cannot be upgraded.
    """

    json_version = from_version

    # Test for incompatible data.
    if data.get(SITE_INFO) is None and data.get(FORECASTS) is None:
        raise SchemaIncompatibleError("Neither siteinfo nor forecasts present")
    if data.get(SITE_INFO) is not None:
        site_info = data.get(SITE_INFO, {})
        site_entry = site_info.get(first_site_id, {}) if first_site_id else {}
        if not isinstance(site_entry.get(FORECASTS), list):
            raise SchemaIncompatibleError("siteinfo forecasts is not a list")
    if data.get(FORECASTS) is not None:
        if not isinstance(data.get(FORECASTS), list):
            raise SchemaIncompatibleError("Top-level forecasts is not a list")

    # V3 and prior versions did not have a version key.
    if json_version < 4:
        data[VERSION] = 4
        json_version = 4

    # Add LAST_ATTEMPT and AUTO_UPDATED as of v5.
    # Ancient v3 versions did not have the SITE_INFO key.
    if json_version < 5:
        _LOGGER.debug("Upgrading to v5 cache structure")
        data[VERSION] = 5
        data[LAST_ATTEMPT] = data[LAST_UPDATED]
        data[AUTO_UPDATED] = auto_update_enabled
        if data.get(SITE_INFO) is None:
            if data.get(FORECASTS) is not None and first_site_id is not None:
                data[SITE_INFO] = {first_site_id: {FORECASTS: data.get(FORECASTS)}}
                data.pop(FORECASTS, None)
                data.pop("energy", None)
        json_version = 5

    # Alter AUTO_UPDATED boolean flag to int, introduced v4.3.0.
    if json_version < 6:
        _LOGGER.debug("Upgrading to v6 cache structure")
        data[VERSION] = 6
        data[AUTO_UPDATED] = 99999 if auto_update_enabled else 0
        json_version = 6

    # Add failure statistics, introduced v4.3.5.
    if json_version < 7:
        _LOGGER.debug("Upgrading to v7 cache structure")
        data[VERSION] = 7
        data[FAILURE] = {LAST_24H: 0, LAST_7D: [0] * 7}
        json_version = 7

    if json_version < 8:
        _LOGGER.debug("Upgrading to v8 cache structure")
        data[VERSION] = 8
        data[FAILURE][LAST_14D] = data[FAILURE][LAST_7D] + [0] * 7
        json_version = 8

    # Add integration version, introduced v4.5.1.
    if json_version < 9:
        _LOGGER.debug("Upgrading to v9 cache structure")
        data[VERSION] = 9
        data[INTEGRATION_VERSION] = "unknown"
        json_version = 9

    # Add success statistics, introduced v4.5.1.
    if json_version < 10:
        _LOGGER.debug("Upgrading to v10 cache structure")
        data[VERSION] = 10
        data[SUCCESS] = {SUCCESS_TRACKED: {}, SUCCESS_FORCED: {}}
        json_version = 10

    return json_version
