"""Auto-discover solar forecast entities from a config entry."""

from __future__ import annotations

from datetime import datetime, date
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


def discover_solar_entities(
    hass: HomeAssistant,
    config_entry_id: str,
) -> dict[str, str]:
    """Discover solar forecast entities belonging to a config entry.

    Returns a dict mapping roles to entity_ids:
        {"remaining": "sensor.xxx", "today": "sensor.xxx",
         "tomorrow": "sensor.xxx", "day_3": "sensor.xxx", ...}

    Detection strategy:
    1. Get all entities belonging to the config entry
    2. For each sensor entity, check attributes to determine forecast type
    3. Read the date from the forecast data to assign day roles
    4. Identify the "remaining" entity separately
    """
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, config_entry_id)

    # Filter to sensor entities only
    sensor_entries = [e for e in entries if e.entity_id.startswith("sensor.")]

    today = date.today()
    result: dict[str, str] = {}
    forecast_entities: list[tuple[str, date]] = []  # (entity_id, forecast_date)

    for entry in sensor_entries:
        entity_id = entry.entity_id
        state = hass.states.get(entity_id)
        if state is None:
            continue

        attrs = state.attributes

        # Check for "remaining" entity by unique_id or original_name
        uid = entry.unique_id or ""
        orig_name = (entry.original_name or "").lower()
        if "remaining" in uid.lower() or "remaining" in orig_name:
            result["remaining"] = entity_id
            continue

        # Detect forecast date from attributes
        forecast_date = _extract_forecast_date(attrs)
        if forecast_date:
            forecast_entities.append((entity_id, forecast_date))

    # Sort by date and assign day roles
    forecast_entities.sort(key=lambda x: x[1])

    for entity_id, fdate in forecast_entities:
        delta = (fdate - today).days
        if delta == 0:
            result["today"] = entity_id
        elif delta == 1:
            result["tomorrow"] = entity_id
        elif 2 <= delta <= 6:
            result[f"day_{delta + 1}"] = entity_id

    return result


def _extract_forecast_date(attrs: dict) -> date | None:
    """Extract the forecast date from entity attributes.

    Supports:
    - Solcast: detailedForecast (list of dicts with period_start)
    - Open-Meteo: watts (dict with timestamp keys) or wh_period (dict with timestamp keys)
    """
    # Solcast: detailedForecast
    detailed = attrs.get("detailedForecast")
    if detailed and isinstance(detailed, list) and len(detailed) > 0:
        first = detailed[0]
        period = first.get("period_start") if isinstance(first, dict) else None
        if period:
            return _parse_date(period)

    # Open-Meteo: watts (96 quarter-hourly entries)
    watts = attrs.get("watts")
    if watts and isinstance(watts, dict):
        first_key = next(iter(watts), None)
        if first_key:
            return _parse_date(first_key)

    # Open-Meteo: wh_period (24 hourly entries)
    wh = attrs.get("wh_period")
    if wh and isinstance(wh, dict):
        first_key = next(iter(wh), None)
        if first_key:
            return _parse_date(first_key)

    return None


def _parse_date(value) -> date | None:
    """Parse a date from a datetime object or ISO string."""
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, str) and "T" in value:
        try:
            return datetime.fromisoformat(value).date()
        except (ValueError, TypeError):
            pass
    return None


def detect_solar_source(attrs: dict) -> str | None:
    """Detect whether an entity is Solcast or Open-Meteo based on attributes.

    Returns "solcast", "open_meteo", or None.
    """
    if attrs.get("detailedForecast"):
        return "solcast"
    if attrs.get("watts") or attrs.get("wh_period"):
        return "open_meteo"
    return None
