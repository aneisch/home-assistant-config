"""HASS devices."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from lennoxs30api.s30api_async import LennoxBle, lennox_equipment, lennox_system, lennox_zone

from .const import LENNOX_DOMAIN, LENNOX_MFG
from .helpers import helper_create_zone_entity_name


class Device:
    """Represent a HASS device."""

    def __init__(self, equipment: lennox_equipment) -> None:
        """Create object."""
        self.equipment: lennox_equipment = equipment

    @property
    def hw_version(self) -> str:
        """Return HW Version."""
        if self.equipment is not None:
            return self.equipment.unit_serial_number
        return None

    @property
    def unique_name(self) -> str:
        """Generate Unique Name."""
        raise NotImplementedError


class S30ControllerDevice(Device):
    """Represents S30 smart hub."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, system: lennox_system) -> None:
        """Create object."""
        super().__init__(system.equipment.get(0))
        self._hass = hass
        self._system = system
        self._config_entry = config_entry

    @property
    def unique_name(self) -> str:
        """Create unique_id."""
        return self._system.unique_id

    def register_device(self) -> None:
        """Register the device with HASS."""
        device_registry = dr.async_get(self._hass)

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            #            connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            suggested_area="basement",
            name=self._system.name,
            model=self._system.productType,
            sw_version=self._system.softwareVersion,
        )


class S30OutdoorUnit(Device):
    """Represents Lennox Outdoor Unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        s30_device: S30ControllerDevice,
    ) -> None:
        """Create object."""
        super().__init__(system.get_outdoor_unit_equipment())
        self._hass = hass
        self._system = system
        self._config_entry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return unique_id."""
        return self._system.unique_id + "_ou"

    @property
    def device_model(self) -> str:
        """Return the device model."""
        if self.equipment is not None:
            return self.equipment.unit_model_number
        return self._system.outdoorUnitType

    def register_device(self) -> None:
        """Register device with HASS."""
        device_registry = dr.async_get(self._hass)
        if self.equipment is not None and self.equipment.equipment_type_name is not None:
            name = f"{self._system.name} {self.equipment.equipment_type_name}"
        elif self._system.outdoorUnitType is not None:
            name = f"{self._system.name} {self._system.outdoorUnitType}"
        else:
            name = f"{self._system.name} outdoor unit"

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            suggested_area="outside",
            name=name,
            model=self.device_model,
            hw_version=self.hw_version,
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
        )


class S30IndoorUnit(Device):
    """Represents Lennox Indoor Unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        s30_device: S30ControllerDevice,
    ) -> None:
        """Create object."""
        super().__init__(system.get_indoor_unit_equipment())
        self._hass = hass
        self._system = system
        self._config_entry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return unique_name."""
        return self._system.unique_id + "_iu"

    @property
    def device_model(self) -> str:
        """Return the device model."""
        if self.equipment is not None:
            return self.equipment.unit_model_number
        return self._system.indoorUnitType

    def register_device(self) -> None:
        """Register device with HASS."""
        device_registry = dr.async_get(self._hass)
        if self.equipment is not None and self.equipment.equipment_type_name is not None:
            name = f"{self._system.name} {self.equipment.equipment_type_name}"
        elif self._system.indoorUnitType is not None:
            name = f"{self._system.name} {self._system.indoorUnitType}"
        else:
            name = f"{self._system.name} indoor unit"

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            suggested_area="basement",
            name=name,
            model=self.device_model,
            hw_version=self.hw_version,
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
        )


class S30AuxiliaryUnit(Device):
    """Represent an Auxiliary Unit like a heat exhanger."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        s30_device: S30ControllerDevice,
        equipment: lennox_equipment,
    ) -> None:
        """Create object."""
        super().__init__(equipment)
        self._hass = hass
        self._system = system
        self._config_entry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return unique name."""
        # Not sure if every device has a serial number.
        if self.equipment.unit_serial_number is None:
            suffix = self.equipment.equipment_id
        else:
            suffix = self.equipment.unit_serial_number
        return f"{self._system.unique_id}_{suffix}"

    @property
    def device_model(self) -> str | None:
        """Return device model."""
        if self.equipment is not None:
            return self.equipment.unit_model_number
        return None

    def register_device(self) -> None:
        """Register the device with HASS."""
        device_registry = dr.async_get(self._hass)
        name = f"{self._system.name} {self.equipment.equipment_type_name}"

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            suggested_area="basement",
            name=name,
            model=self.device_model,
            hw_version=self.hw_version,
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
        )


class S30VentilationUnit(Device):
    """Represents a ventilation unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        s30_device: S30ControllerDevice,
    ) -> None:
        super().__init__(None)
        self._hass = hass
        self._system = system
        self._config_entry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return unique_name."""
        suffix = "ventilation"
        return f"{self._system.unique_id}_{suffix}"

    @property
    def device_model(self) -> str:
        """Return the device model."""
        if self._system.ventilationUnitType == "ventilation":
            return "Fresh Air Damper"
        return self._system.ventilationUnitType

    def register_device(self) -> None:
        """Register the device with HASS."""
        device_registry = dr.async_get(self._hass)
        name = f"{self._system.name} Ventilator"

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            suggested_area="basement",
            name=name,
            model=self.device_model,
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
        )


class S30ZoneThermostat(Device):
    """Represents a thermostat."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        zone: lennox_zone,
        s30_device: S30ControllerDevice,
    ) -> None:
        """Create object."""
        Device.__init__(self, None)
        self._hass = hass
        self._system = system
        self._zone = zone
        self._config_entry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return unique_name."""
        return self._zone.unique_id

    def register_device(self) -> None:
        """Register the device with HASS."""
        device_registry = dr.async_get(self._hass)
        name = helper_create_zone_entity_name(self._system, self._zone)

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            name=name,
            model="thermostat",
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
        )


def helper_create_ble_device_id(system: lennox_system, ble_device: LennoxBle) -> str:
    """Construct a device id for Lennox BLE device."""
    return f"{system.unique_id}_ble_{ble_device.ble_id}"


class S40BleDevice(Device):
    """Represents a BLE device."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        system: lennox_system,
        ble_device: LennoxBle,
        s30_device: S30ControllerDevice,
    ) -> None:
        """Create object."""
        Device.__init__(self, None)
        self._hass: HomeAssistant = hass
        self._system: lennox_system = system
        self._ble_device: LennoxBle = ble_device
        self._config_entry: ConfigEntry = config_entry
        self._s30_controller_device: S30ControllerDevice = s30_device

    @property
    def unique_name(self) -> str:
        """Return  unique_name."""
        return helper_create_ble_device_id(self._system, self._ble_device)

    def register_device(self) -> None:
        """Register the device with HASS."""
        device_registry = dr.async_get(self._hass)

        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(LENNOX_DOMAIN, self.unique_name)},
            manufacturer=LENNOX_MFG,
            name=self._system.name + " " + self._ble_device.deviceName,
            model=self._ble_device.controlModelNumber,
            via_device=(LENNOX_DOMAIN, self._s30_controller_device.unique_name),
            sw_version=self._ble_device.controlSoftwareVersion,
            hw_version=self._ble_device.controlHardwareVersion,
        )
