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

# Home Assistant 2026.8 added `via_device_id` to DeviceInfo and deprecated
# `via_device`, which stops working in 2027.8. Older releases reject the new key.
VIA_DEVICE_ID_SUPPORTED = "via_device_id" in DeviceInfo.__optional_keys__

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

    # Remove any leaf devices that are no longer selected in options from the
    # device registry. OptionsFlowWithReload triggers a reload after options
    # change, so this runs on every setup and cleans up de-selected devices.
    configured_ids = set(entry.options.get(CONF_DEVICES, []))
    leaf_device_ids = {
        str(d["id"]) for d in all_devices if d.get("type") != DEVICE_BRIDGE
    }
    if removed_device_ids := leaf_device_ids - configured_ids:
        await remove_devices_from_registry(hass, entry.entry_id, removed_device_ids)

    # Register bridges before any platform loads, so child devices can point at
    # a bridge that already exists in the device registry. Record each bridge's
    # gateway topic and registry id for the entities to look up.
    # Bridges are always included by filter_configured_devices.
    device_registry = dr.async_get(hass)
    gateway_to_bridge: dict[str, str] = {}
    bridge_device_ids: dict[str, str] = {}
    for device in devices:
        if device.get("type") != DEVICE_BRIDGE:
            continue
        bridge_id = device.get("id")
        if not bridge_id:
            continue
        bridge_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, **build_device_info(device)
        )
        bridge_device_ids[bridge_id] = bridge_entry.id
        if gateway_topic := device.get("device_gateway_topic"):
            gateway_to_bridge[gateway_topic] = bridge_id
    coordinator.gateway_to_bridge = gateway_to_bridge
    coordinator.bridge_device_ids = bridge_device_ids

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "devices": devices,
        "programs": programs,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, client.stop)

    return True


async def remove_devices_from_registry(
    hass: HomeAssistant, entry_id: str, device_ids: set[str]
) -> None:
    """Remove this entry's devices from the registry by their B-hyve ids."""
    device_registry = dr.async_get(hass)
    identifiers = {(DOMAIN, device_id) for device_id in device_ids}

    for device in dr.async_entries_for_config_entry(device_registry, entry_id):
        if device.identifiers.isdisjoint(identifiers):
            continue
        _LOGGER.info("Removing device %s from registry", device.identifiers)
        try:
            device_registry.async_remove_device(device.id)
        except HomeAssistantError:
            _LOGGER.exception("Failed to remove device %s from registry", device.id)


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


def build_device_info(device: BHyveDevice) -> DeviceInfo:
    """Describe a B-hyve device for the device registry."""
    device_id = device.get("id", "")
    connections: set[tuple[str, str]] = set()
    if mac_address := device.get("mac_address"):
        # Format raw MAC (e.g. "4467552a366e") with colons
        raw = mac_address.replace(":", "").replace("-", "").lower()
        formatted_mac = ":".join(raw[i : i + 2] for i in range(0, len(raw), 2))
        connections.add((CONNECTION_NETWORK_MAC, formatted_mac))

    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        connections=connections,
        manufacturer=MANUFACTURER,
        configuration_url=f"https://techsupport.orbitbhyve.com/dashboard/support/device/{device_id}",
        name=device.get("name", ""),
        model=device.get("hardware_version"),
        hw_version=device.get("hardware_version"),
        sw_version=device.get("firmware_version"),
    )


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

        device_info = build_device_info(device)

        # Link non-bridge devices to their bridge via device_gateway_topic
        if self._device_type != DEVICE_BRIDGE:
            gateway_topic = device.get("device_gateway_topic")
            gateway_to_bridge = getattr(coordinator, "gateway_to_bridge", {})
            bridge_id = gateway_to_bridge.get(gateway_topic) if gateway_topic else None
            if bridge_id and VIA_DEVICE_ID_SUPPORTED:
                # async_setup_entry registered the bridge, so its id is known.
                bridge_device_ids = getattr(coordinator, "bridge_device_ids", {})
                if bridge_entry_id := bridge_device_ids.get(bridge_id):
                    device_info["via_device_id"] = bridge_entry_id
            elif bridge_id:
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
