"""Redaction and key-formatting helpers for logs and diagnostics."""

import re


def format_site_key(site_id: str) -> str:
    """Convert a site ID to a safe dictionary key by replacing hyphens with underscores."""

    return site_id.replace("-", "_")


def redact_api_key(api_key: str) -> str:
    """Obfuscate API key."""

    return "*" * 6 + api_key[-6:]


def redact_msg_api_key(msg: str, api_key: str) -> str:
    """Obfuscate API key in messages."""

    return (
        msg.replace("key=" + api_key, "key=" + redact_api_key(api_key))
        .replace("key': '" + api_key, "key': '" + redact_api_key(api_key))
        .replace("sites-" + api_key, "sites-" + redact_api_key(api_key))
        .replace("usage-" + api_key, "usage-" + redact_api_key(api_key))
    )


def redact_filename_api_key(filename: str) -> str:
    """Obfuscate API key in filenames."""

    parts = filename.split("-")
    if len(parts) == 4 and (parts[1] == "sites" or parts[1] == "usage"):
        api_key = parts[2]
        return filename.replace(api_key, redact_api_key(api_key))
    return filename


def redact_lat_lon_simple(s: str) -> str:
    """Redact latitude and longitude decimal places in a string."""

    return re.sub(r"\.[0-9]+", ".******", s)


def redact_lat_lon(s: str) -> str:
    """Redact latitude and longitude in a string."""

    return re.sub(r"itude\': [0-9\-\.]+", "itude': **.******", s)
