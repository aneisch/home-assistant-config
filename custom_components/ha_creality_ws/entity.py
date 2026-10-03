from __future__ import annotations
from homeassistant.helpers.device_registry import DeviceInfo #type: ignore[import]
from homeassistant.helpers.update_coordinator import CoordinatorEntity #type: ignore[import]

from .const import DOMAIN, MFR, MODEL
from .utils import parse_model_version


class KEntity(CoordinatorEntity):
    """Base entity for Creality K-series over WebSocket."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, name: str | None = None, unique_id: str = "", translation_key: str | None = None):
        if not unique_id:
            raise ValueError(f"{type(self).__name__} must provide a non-empty unique_id")
        super().__init__(coordinator)
        effective_tk = translation_key or getattr(self, "_attr_translation_key", None)
        if effective_tk is not None:
            self._attr_translation_key = effective_tk
        elif name:
            self._attr_name = name
        self._attr_unique_id = f"{coordinator.client._host}-{unique_id}"
        self._host = coordinator.client._host

    @property
    def available(self) -> bool:
        # If power switch is configured and OFF, entity is unavailable.
        if self.coordinator.power_is_off():
            return False
            
        return self.coordinator.available

    # Helper used by sensors to decide zeroing
    def _should_zero(self) -> bool:
        """
        Helper to determine if an entity should show a zero/off/none value.
        """
        coord = self.coordinator
        # Returns True if connection is lost OR if the power switch is off.
        return (not coord.available) or coord.power_is_off()
    
    def _get_cached_device_info(self) -> dict | None:
        """
        Get cached device info from config entry (model, hostname, modelVersion).
        Returns None if not available.
        """
        entry = self.coordinator.config_entry
        if not entry or not entry.data.get("_device_info_cached"):
            return None
        return {
            "model": entry.data.get("_cached_model"),
            "hostname": entry.data.get("_cached_hostname"),
            "modelVersion": entry.data.get("_cached_model_version"),
        }

    def _get_cached_max_temps(self) -> dict[str, float | None]:
        """
        Get cached max temperature values from config entry.
    Returns dict with max_bed_temp, max_nozzle_temp, max_box_temp keys.
        Falls back to live data if cached values are not available.

        The fallback is per *field*, not per entry. `_device_info_cached` is set
        as soon as the model is known, but `maxBoxTemp` is a late-discovery
        field, so an entry can carry the flag with a `None` chamber max. Treating
        the flag as proof that every value exists then masked live telemetry and
        pinned the chamber target slider to the 60 degree default in number.py.
        """
        d = self.coordinator.data or {}
        live = {
            "max_bed_temp": d.get("maxBedTemp"),
            "max_nozzle_temp": d.get("maxNozzleTemp"),
            "max_box_temp": d.get("maxBoxTemp"),
        }

        entry = self.coordinator.config_entry
        if entry and entry.data.get("_device_info_cached"):
            cached = {
                "max_bed_temp": entry.data.get("_cached_max_bed_temp"),
                "max_nozzle_temp": entry.data.get("_cached_max_nozzle_temp"),
                # Prefer the chamber cache, falling back to the legacy box one
                # for entries cached by a pre-rename release.
                "max_box_temp": entry.data.get(
                    "_cached_max_chamber_temp", entry.data.get("_cached_max_box_temp")
                ),
            }
            return {
                key: (value if value is not None else live[key])
                for key, value in cached.items()
            }

        return {
            "max_bed_temp": live["max_bed_temp"],
            "max_nozzle_temp": live["max_nozzle_temp"],
            "max_box_temp": live["max_box_temp"],
        }

    @property
    def device_info(self) -> DeviceInfo:
        # First try to get cached device info from entry
        cached_info = self._get_cached_device_info()
        if cached_info and cached_info.get("model"):
            hw_ver, sw_ver = parse_model_version(cached_info.get("modelVersion"))
            return DeviceInfo(
                identifiers={(DOMAIN, self._host)},
                manufacturer=MFR,
                model=cached_info.get("model"),
                name=cached_info.get("hostname") or f"{cached_info.get('model')} (Creality)",
                configuration_url=f"http://{self._host}/",
                hw_version=hw_ver,
                sw_version=sw_ver,
            )
        
        # Fallback to current telemetry (for backwards compatibility)
        d = self.coordinator.data or {}
        model = d.get("model") or MODEL
        hostname = d.get("hostname")

        # Clean firmware/hardware versions
        hw_ver, sw_ver = parse_model_version(d.get("modelVersion"))

        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            manufacturer=MFR,
            model=model,
            name=hostname or f"{model} (Creality)",
            configuration_url=f"http://{self._host}/",
            hw_version=hw_ver,
            sw_version=sw_ver,
        )
