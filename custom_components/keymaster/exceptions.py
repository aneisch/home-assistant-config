"""Exceptions for keymaster."""
from homeassistant.exceptions import HomeAssistantError


class ZWaveIntegrationNotConfiguredError(HomeAssistantError):
    """Raised when a zwave integration is not configured."""

    def __str__(self) -> str:
        return (
            "A Z-Wave integration has not been configured for this "
            "Home Assistant instance"
        )


class NoNodeSpecifiedError(HomeAssistantError):
    """Raised when a node was not specified as an input parameter."""


class ZWaveNetworkNotReady(HomeAssistantError):
    """Raised when Z-Wave network is not ready."""


class NotFoundError(HomeAssistantError):
    """Raised when a Z-Wave items is not found."""


class NotSupportedError(HomeAssistantError):
    """Raised when action is not supported."""
