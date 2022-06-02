"""Constants for readme."""
import logging

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN = "readme"
DOMAIN_DATA = "readme_data"
INTEGRATION_VERSION = "0.5.0"

ISSUE_URL = "https://github.com/custom-components/readme/issues"


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{DOMAIN}
Version: {INTEGRATION_VERSION}
This is a custom integration
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""