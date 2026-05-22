"""Sensor platform for Sunrise SoC Forecast."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **entry.options}
    num_days = config.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS)

    entities = []

    # Day 1-N forecast sensors
    for day in range(1, num_days + 1):
        entities.append(SunriseSocSensor(coordinator, day, entry))

    # Consumption average sensors
    entities.append(ConsumptionAverageSensor(coordinator, "daily", entry))
    entities.append(ConsumptionAverageSensor(coordinator, "overnight", entry))

    async_add_entities(entities)


class SunriseSocSensor(SensorEntity):
    """Sensor for predicted sunrise SoC."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:battery-clock"

    def __init__(
        self,
        coordinator,
        day: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self._coordinator = coordinator
        self._day = day
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sunrise_soc_day_{day}"
        self._attr_name = f"Predicted Sunrise SoC Day {day}"

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister update callback."""
        self._coordinator.unregister_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator update."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the SoC percentage."""
        result = self._coordinator.results.get(self._day)
        if result is None:
            return None
        return result.soc_percent

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        result = self._coordinator.results.get(self._day)
        if result is None:
            return {}

        attrs = {
            "predicted_kwh": result.predicted_kwh,
            "daytime_consumption_kwh": result.daytime_consumption_kwh,
            "backup_charged_kwh": result.backup_charged_kwh,
            "grid_needed_kwh": result.grid_needed_kwh,
            "grid_used_today_kwh": self._coordinator.grid_energy_today,
            "target_soc": self._coordinator.target_soc,
        }

        if self._day == 1:
            attrs["mode"] = "nighttime" if self._coordinator.is_overnight else "daytime"
            attrs["remaining_solar_kwh"] = result.solcast_kwh if not self._coordinator.is_overnight else 0
            attrs["using_fallback"] = self._coordinator.get_consumption().using_fallback
        else:
            attrs["solcast_kwh"] = result.solcast_kwh
            attrs["morning_low_kwh"] = result.morning_low_kwh
            attrs["morning_low_pct"] = result.morning_low_pct
            if result.floor_hour:
                attrs["floor_hour"] = result.floor_hour
            if result.night_floor_hour:
                attrs["night_floor_hour"] = result.night_floor_hour

        return attrs


class ConsumptionAverageSensor(SensorEntity):
    """Sensor for 7-day consumption average."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "kWh"

    def __init__(
        self,
        coordinator,
        period: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self._coordinator = coordinator
        self._period = period
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_7day_avg_{period}"
        self._attr_name = f"7 Day Average {'Daily' if period == 'daily' else 'Overnight'} Consumption"

    async def async_added_to_hass(self) -> None:
        """Register update callback."""
        self._coordinator.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister update callback."""
        self._coordinator.unregister_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle coordinator update."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the average."""
        if self._period == "daily":
            return self._coordinator.daily_average
        return self._coordinator.overnight_average

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return history and hourly breakdown."""
        if self._period == "daily":
            history = self._coordinator.daily_history
        else:
            history = self._coordinator.overnight_history

        attrs = {"history": history, "days": len(history)}

        # Add hourly averages
        hourly = self._coordinator.get_hourly_averages()
        attrs["hourly_averages"] = hourly
        attrs["hourly_detail"] = {
            f"{h:02d}:00": round(hourly[h], 2) for h in range(24)
        }
        attrs["hourly_history"] = {
            f"{h:02d}:00": ", ".join(f"{v:05.2f}" for v in self._coordinator._hourly_history[h])
            for h in range(24)
            if self._coordinator._hourly_history[h]
        }

        return attrs
