"""Sunrise SoC Forecast integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)

from .const import (
    DOMAIN,
    CONF_MAIN_SOC_ENTITY,
    CONF_MAIN_POWER_ENTITY,
    CONF_BACKUP_ENABLED,
    CONF_BACKUP_SOC_ENTITY,
    CONF_BACKUP_DISCHARGE_ENTITY,
    CONF_SOLCAST_REMAINING,
    CONF_SOLCAST_FORECAST_TODAY,
    CONF_GRID_POWER_ENTITY,
)
from .coordinator import SunriseSocCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sunrise SoC Forecast from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Merge options into data for the coordinator
    config = {**entry.data, **entry.options}

    coordinator = SunriseSocCoordinator(hass, config, entry.entry_id)
    await coordinator.async_load()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Store unsub callables for cleanup on unload (fix #2)
    unsubs = []

    # Track house load power sensor for energy accumulation + forecast updates
    power_entity = config[CONF_MAIN_POWER_ENTITY]

    @callback
    def _power_change_listener(event) -> None:
        """Accumulate energy and recalculate on every power reading."""
        coordinator.accumulate_energy()
        coordinator.update()

    unsubs.append(
        async_track_state_change_event(hass, [power_entity], _power_change_listener)
    )

    # Track other entities for forecast updates only (no accumulation)
    forecast_entities = [config[CONF_MAIN_SOC_ENTITY]]

    if config.get(CONF_BACKUP_ENABLED):
        if CONF_BACKUP_SOC_ENTITY in config:
            forecast_entities.append(config[CONF_BACKUP_SOC_ENTITY])
        if CONF_BACKUP_DISCHARGE_ENTITY in config:
            forecast_entities.append(config[CONF_BACKUP_DISCHARGE_ENTITY])

    # Track all Solcast entities for forecast updates
    from .const import SOLCAST_STANDARD
    for conf_key in SOLCAST_STANDARD.values():
        entity = config.get(conf_key, "")
        if entity:
            forecast_entities.append(entity)
    solcast_remaining = config.get(CONF_SOLCAST_REMAINING, "")
    if solcast_remaining and solcast_remaining not in forecast_entities:
        forecast_entities.append(solcast_remaining)
    solcast_today = config.get(CONF_SOLCAST_FORECAST_TODAY, "")
    if solcast_today and solcast_today not in forecast_entities:
        forecast_entities.append(solcast_today)

    @callback
    def _forecast_change_listener(event) -> None:
        """Recalculate forecast on sensor changes."""
        coordinator.update()

    unsubs.append(
        async_track_state_change_event(hass, forecast_entities, _forecast_change_listener)
    )

    # Track each sensor-mode dump load for energy integration + forecast updates
    def _make_dump_load_listener(load_idx: int):
        @callback
        def _dump_load_change(event) -> None:
            coordinator.accumulate_dump_load(load_idx)
            coordinator.update()
        return _dump_load_change

    for idx, tracker in enumerate(coordinator.dump_loads):
        if tracker.get("type") != "sensor":
            continue
        entity = tracker.get("power_entity")
        if not entity:
            continue
        unsubs.append(
            async_track_state_change_event(
                hass, [entity], _make_dump_load_listener(idx)
            )
        )

    # Track grid power sensor for import accumulation
    grid_entity = config.get(CONF_GRID_POWER_ENTITY, "")
    if grid_entity:

        @callback
        def _grid_change_listener(event) -> None:
            """Accumulate grid import energy."""
            coordinator.accumulate_grid()

        unsubs.append(
            async_track_state_change_event(hass, [grid_entity], _grid_change_listener)
        )

    # Pre-midnight: freeze solar data before entities shift at midnight
    @callback
    def _pre_midnight_handler(now) -> None:
        coordinator.on_pre_midnight()

    unsubs.append(
        async_track_time_change(hass, _pre_midnight_handler, hour=23, minute=55, second=0)
    )

    # Midnight: record daily consumption and reset accumulator
    @callback
    def _midnight_handler(now) -> None:
        coordinator.on_midnight()
        coordinator.update()

    unsubs.append(
        async_track_time_change(hass, _midnight_handler, hour=0, minute=0, second=5)
    )

    # Save state before HA stops (preserves mid-hour energy accumulators)
    @callback
    def _on_ha_stop(event) -> None:
        hass.async_create_task(coordinator.async_save())

    unsubs.append(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_ha_stop)
    )

    # Store unsubs on coordinator for cleanup
    coordinator.unsubs = unsubs

    # Reload on options change (fix #7)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Initial update
    coordinator.update()

    _LOGGER.info(
        "Sunrise SoC Forecast loaded: %d days, %s backup battery",
        coordinator.num_days,
        "with" if coordinator.backup.enabled else "no",
    )

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    # Save state before unloading (preserves frozen data and accumulators)
    if coordinator:
        await coordinator.async_save()

    # Unsubscribe all event listeners
    if coordinator and hasattr(coordinator, "unsubs"):
        for unsub in coordinator.unsubs:
            unsub()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
