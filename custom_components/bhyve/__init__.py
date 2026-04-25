"""Support for Orbit BHyve irrigation devices."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.bhyve.pybhyve.typings import BHyveDevice

from .const import (
    CONF_DEVICES,
    DEVICE_BRIDGE,
    DOMAIN,
    EVENT_PROGRAM_CHANGED,
    LOGGER,
    MANUFACTURER,
)
from .coordinator import BHyveDataUpdateCoordinator
from .pybhyve import BHyveClient
from .pybhyve.errors import AuthenticationError, BHyveError
from .util import filter_configured_devices

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BHyve from a config entry."""
    client = BHyveClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )

    try:
        if await client.login() is False:
            _LOGGER.warning("Invalid credentials for %s", entry.data[CONF_USERNAME])
            msg = "Invalid credentials"
            raise ConfigEntryAuthFailed(msg)
    except AuthenticationError as err:
        _LOGGER.warning("Authentication failed for %s", entry.data[CONF_USERNAME])
        raise ConfigEntryAuthFailed(err) from err
    except (BHyveError, TimeoutError) as err:
        raise ConfigEntryNotReady(err) from err

    # Create coordinator
    coordinator = BHyveDataUpdateCoordinator(hass, client, entry)

    # Initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # WebSocket callback routes to coordinator
    async def async_update_callback(data: dict) -> None:
        event = data.get("event")

        # Route to coordinator - coordinator handles all entity updates
        if event == EVENT_PROGRAM_CHANGED:
            await coordinator.async_handle_program_event(data)
        else:
            await coordinator.async_handle_device_event(data)

    # Start WebSocket
    client.listen(hass.loop, async_update_callback)

    # Filter the device list to those that are enabled in options
    try:
        all_devices = await client.devices
        programs = await client.timer_programs
    except (BHyveError, TimeoutError) as err:
        raise ConfigEntryNotReady(err) from err
    devices = filter_configured_devices(entry, all_devices)

    # Build a mapping from device_gateway_topic to bridge device ID
    # so child devices can reference their bridge via via_device.
    # Bridges are always included by filter_configured_devices.
    gateway_to_bridge: dict[str, str] = {}
    for device in devices:
        if device.get("type") == DEVICE_BRIDGE:
            gateway_topic = device.get("device_gateway_topic")
            if gateway_topic:
                gateway_to_bridge[gateway_topic] = device.get("id", "")
    coordinator.gateway_to_bridge = gateway_to_bridge

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "devices": devices,
        "programs": programs,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, client.stop)

    return True


async def remove_devices_from_registry(
    hass: HomeAssistant, device_ids: set[str]
) -> None:
    """Remove devices from registry by domain-specific string identifiers."""
    device_registry = dr.async_get(hass)

    for device_id in device_ids:
        # Find the device in the registry by its identifiers
        device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
        if device:
            _LOGGER.info("Removing device %s from registry", device_id)
            try:
                device_registry.async_remove_device(device.id)
            except HomeAssistantError:
                _LOGGER.exception("Failed to remove device %s from registry", device_id)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload to update options and remove filtered devices."""
    # Get the current client and all devices before reload
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data:
        client = data["client"]
        try:
            all_devices = await client.devices
            # Get currently configured device IDs
            configured_ids = set(entry.options.get(CONF_DEVICES, []))

            # Find leaf devices that were removed from configuration
            # (bridges are always included and not user-selectable)
            leaf_device_ids = {
                str(d["id"]) for d in all_devices if d.get("type") != DEVICE_BRIDGE
            }
            removed_device_ids = leaf_device_ids - configured_ids

            if removed_device_ids:
                # Remove devices from Home Assistant
                await remove_devices_from_registry(hass, removed_device_ids)
        except (BHyveError, KeyError, TimeoutError) as err:
            _LOGGER.warning("Error checking for removed devices: %s", err)

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data:
        client = data.get("client")
        if client:
            await client.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class BHyveCoordinatorEntity(CoordinatorEntity[BHyveDataUpdateCoordinator]):
    """Base entity for coordinator-based B-hyve entities."""

    def __init__(
        self,
        coordinator: BHyveDataUpdateCoordinator,
        device: BHyveDevice,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device.get("id", "")
        self._device_type = device.get("type", "")
        self._device_name = device.get("name", "")
        self._mac_address = device.get("mac_address")

        # Device info for grouping
        connections: set[tuple[str, str]] = set()
        if self._mac_address:
            # Format raw MAC (e.g. "4467552a366e") with colons
            raw = self._mac_address.replace(":", "").replace("-", "").lower()
            formatted_mac = ":".join(raw[i : i + 2] for i in range(0, len(raw), 2))
            connections.add((CONNECTION_NETWORK_MAC, formatted_mac))

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            connections=connections,
            manufacturer=MANUFACTURER,
            configuration_url=f"https://techsupport.orbitbhyve.com/dashboard/support/device/{self._device_id}",
            name=self._device_name,
            model=device.get("hardware_version"),
            hw_version=device.get("hardware_version"),
            sw_version=device.get("firmware_version"),
        )

        # Link non-bridge devices to their bridge via device_gateway_topic
        if self._device_type != DEVICE_BRIDGE:
            gateway_topic = device.get("device_gateway_topic")
            gateway_to_bridge = getattr(coordinator, "gateway_to_bridge", {})
            bridge_id = gateway_to_bridge.get(gateway_topic) if gateway_topic else None
            if bridge_id:
                device_info["via_device"] = (DOMAIN, bridge_id)

        self._attr_device_info = device_info

        LOGGER.debug(
            "Creating %s: %s - %s",
            self.__class__.__name__,
            self._device_name,
            getattr(self, "_attr_name", None) or self._device_name,
        )

    @property
    def device_data(self) -> dict[str, Any]:
        """Get device data from coordinator."""
        return (
            self.coordinator.data.get("devices", {})
            .get(self._device_id, {})
            .get("device", {})
        )

    @property
    def available(self) -> bool:
        """Entity available when device connected."""
        return self.device_data.get("is_connected", False)
