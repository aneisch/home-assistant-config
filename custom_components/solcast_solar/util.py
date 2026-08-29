"""Solcast utilities."""

import math
from typing import Any

from .log import get_logger

_LOGGER = get_logger(__name__)


def split_and_strip(value: str) -> list[str]:
    """Split a comma-separated string and strip whitespace, discarding empty items."""

    return [item.strip() for item in value.split(",") if item.strip()]


def azimuth_to_compass_degrees(azimuth: Any) -> float | None:
    """Convert Solcast azimuth to compass degrees in the range [0, 360).

    Solcast azimuth uses N=0, W=+90, E=-90, S=+/-180.
    Standard compass bearings use N=0, E=90, S=180, W=270.
    """
    try:
        return (-float(azimuth)) % 360.0
    except (TypeError, ValueError):
        return None


def azimuth_to_compass_direction(azimuth: Any) -> str | None:
    """Convert an azimuth value to a 16-point cardinal compass direction."""
    if (compass_degrees := azimuth_to_compass_degrees(azimuth)) is None:
        return None

    directions = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )
    return directions[int((compass_degrees + 11.25) // 22.5) % len(directions)]


def percentile(data: list[Any], _percentile: float) -> float | int:
    """Find the given percentile in a sorted list of values."""

    if not data:
        return 0.0
    k = (len(data) - 1) * (_percentile / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return round(d0 + d1, 4)


def ordinal(value: int) -> str:
    """Return a number with an ordinal suffix."""

    abs_value = abs(value)
    return f"{value}{'th' if 11 <= abs_value % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(abs_value % 10, 'th')}"


def interquartile_bounds(sorted_data: list[Any], factor: float = 1.5) -> tuple[float | int, float | int]:
    """Return the lower and upper interquartile bounds of a sorted data set."""

    lower = 0.0
    upper = float("inf")
    iqr = 0.0
    if len(sorted_data) > 4:
        q1 = percentile(sorted_data, 25)
        q3 = percentile(sorted_data, 75)
        iqr = round(q3 - q1, 5)
        lower = round(q1 - factor * iqr, 4)
        upper = round(q3 + factor * iqr, 4)
    return (lower, upper)


def diff(lst: list[Any], non_negative: bool = True) -> list[Any]:
    """Build a numpy-like diff."""

    size = len(lst) - 1
    r: list[int | float] = [0] * size
    for i in range(size):
        r[i] = max(0, lst[i + 1] - lst[i]) if non_negative else lst[i + 1] - lst[i]
    return r
