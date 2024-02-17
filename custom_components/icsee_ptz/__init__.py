"""Support for ICSee devices."""
from .config_flow import async_get_entry_data
from .camera import Camera
from .const import DOMAIN
import logging
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, callback

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.

    cam = Camera(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    entry.async_create_background_task(
        hass, cam.async_ensure_alive(), "DVRIPCam connections"
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = cam

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener. Called when integration options are changed"""
    await hass.config_entries.async_reload(entry.entry_id)
