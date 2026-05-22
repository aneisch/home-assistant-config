"""Config flow for Sunrise SoC Forecast integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MAIN_SOC_ENTITY,
    CONF_MAIN_POWER_ENTITY,
    CONF_MAIN_CAPACITY,
    CONF_MAIN_FLOOR,
    CONF_BACKUP_ENABLED,
    CONF_BACKUP_SOC_ENTITY,
    CONF_BACKUP_DISCHARGE_ENTITY,
    CONF_BACKUP_CAPACITY,
    CONF_BACKUP_FLOOR,
    CONF_BACKUP_DISCHARGE_KW,
    CONF_BACKUP_ACTIVATION_HOUR,
    CONF_DEFAULT_DAILY,
    CONF_DEFAULT_OVERNIGHT,
    CONF_GUARD_THRESHOLD,
    CONF_SOLCAST_REMAINING,
    CONF_SOLCAST_FORECAST_TODAY,
    CONF_SOLCAST_TOMORROW,
    CONF_SOLCAST_DAY_3,
    CONF_SOLCAST_DAY_4,
    CONF_SOLCAST_DAY_5,
    CONF_SOLCAST_DAY_6,
    CONF_SOLCAST_DAY_7,
    CONF_GRID_POWER_ENTITY,
    CONF_BACKUP_MODE,
    CONF_BACKUP_CHARGE_EFFICIENCY,
    CONF_BACKUP_DISCHARGE_EFFICIENCY,
    CONF_MAIN_INVERTER_EFFICIENCY,
    BACKUP_MODE_ALWAYS,
    BACKUP_MODE_TARGET,
    CONF_FORECAST_DAYS,
    CONF_TARGET_SOC,
    CONF_SOLAR_SOURCE,
    CONF_SOLAR_CONFIG_ENTRY,
    CONF_SOLAR_ENTITY_REMAINING,
    CONF_SOLAR_ENTITY_TODAY,
    CONF_SOLAR_ENTITY_TOMORROW,
    CONF_SOLAR_ENTITY_DAY_3,
    CONF_SOLAR_ENTITY_DAY_4,
    CONF_SOLAR_ENTITY_DAY_5,
    CONF_SOLAR_ENTITY_DAY_6,
    CONF_SOLAR_ENTITY_DAY_7,
    SOLAR_SOURCE_MANUAL,
    SOLAR_DOMAINS,
    DEFAULT_MAIN_CAPACITY,
    DEFAULT_MAIN_FLOOR,
    DEFAULT_BACKUP_CAPACITY,
    DEFAULT_BACKUP_FLOOR,
    DEFAULT_BACKUP_DISCHARGE_KW,
    DEFAULT_BACKUP_ACTIVATION_HOUR,
    DEFAULT_DAILY_CONSUMPTION,
    DEFAULT_OVERNIGHT_CONSUMPTION,
    DEFAULT_GUARD_THRESHOLD,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_TARGET_SOC,
    DEFAULT_MAIN_INVERTER_EFFICIENCY,
    DEFAULT_BACKUP_CHARGE_EFFICIENCY,
    DEFAULT_BACKUP_DISCHARGE_EFFICIENCY,
    CONF_DUMP_LOADS,
    CONF_DUMP_LOAD_NAME,
    CONF_DUMP_LOAD_TYPE,
    CONF_DUMP_LOAD_AVG_KW,
    CONF_DUMP_LOAD_START_HOUR,
    CONF_DUMP_LOAD_END_HOUR,
    CONF_DUMP_LOAD_HOURLY_PROFILE,
    CONF_DUMP_LOAD_ADVANCED,
    CONF_DUMP_LOAD_POWER_ENTITY,
    DUMP_LOAD_TYPE_MANUAL,
    DUMP_LOAD_TYPE_SENSOR,
    DEFAULT_DUMP_LOAD_AVG_KW,
    DEFAULT_DUMP_LOAD_START_HOUR,
    DEFAULT_DUMP_LOAD_END_HOUR,
)
from .solar_discovery import discover_solar_entities

_LOGGER = logging.getLogger(__name__)

ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)


class DumpLoadFlowMixin:
    """Shared dump-load steps for ConfigFlow and OptionsFlow.

    The host class must provide:
      - ``self._data`` accumulating dict
      - ``async_step_solar_source`` (the next step after dump loads)
      - optionally ``_get_existing_dump_loads`` (for OptionsFlow seeding)
    """

    _data: dict
    _editing_dump_load_index: int | None = None
    _pending_dump_load: dict | None = None

    def _get_existing_dump_loads(self) -> list[dict]:
        """Return dump loads from existing entry — overridden by OptionsFlow."""
        return []

    async def _dump_loads_done(self):
        """Next step after Continue on the dump-loads menu — override for OptionsFlow."""
        return await self.async_step_solar_source()

    def _ensure_dump_loads_seeded(self) -> None:
        if CONF_DUMP_LOADS not in self._data:
            self._data[CONF_DUMP_LOADS] = [dict(d) for d in self._get_existing_dump_loads()]

    def _get_editing_load(self) -> dict:
        if self._editing_dump_load_index is None:
            return {}
        loads = self._data.get(CONF_DUMP_LOADS, [])
        if 0 <= self._editing_dump_load_index < len(loads):
            return loads[self._editing_dump_load_index]
        return {}

    def _commit_dump_load(self, load: dict) -> None:
        loads = self._data[CONF_DUMP_LOADS]
        if (
            self._editing_dump_load_index is not None
            and 0 <= self._editing_dump_load_index < len(loads)
        ):
            loads[self._editing_dump_load_index] = load
        else:
            loads.append(load)
        self._editing_dump_load_index = None
        self._pending_dump_load = None

    async def async_step_dump_loads(self, user_input=None):
        """List/add/edit/remove dump loads. Continue → solar_source."""
        self._ensure_dump_loads_seeded()
        loads: list[dict] = self._data[CONF_DUMP_LOADS]

        if user_input is not None:
            action = user_input["action"]
            if action == "continue":
                return await self._dump_loads_done()
            if action == "add":
                self._editing_dump_load_index = None
                self._pending_dump_load = None
                return await self.async_step_dump_load_type()
            if action.startswith("edit_"):
                idx = int(action[len("edit_"):])
                if 0 <= idx < len(loads):
                    self._editing_dump_load_index = idx
                    if loads[idx].get(CONF_DUMP_LOAD_TYPE) == DUMP_LOAD_TYPE_SENSOR:
                        return await self.async_step_dump_load_sensor()
                    return await self.async_step_dump_load_manual()
            elif action.startswith("remove_"):
                idx = int(action[len("remove_"):])
                if 0 <= idx < len(loads):
                    loads.pop(idx)
            # fall through: re-render menu

        options_list: list[selector.SelectOptionDict] = [
            selector.SelectOptionDict(value="add", label="Add new dump load"),
        ]
        for i, load in enumerate(loads):
            name = load.get(CONF_DUMP_LOAD_NAME) or f"Load {i + 1}"
            type_label = (
                "manual"
                if load.get(CONF_DUMP_LOAD_TYPE) == DUMP_LOAD_TYPE_MANUAL
                else "sensor"
            )
            options_list.append(
                selector.SelectOptionDict(
                    value=f"edit_{i}", label=f"Edit: {name} ({type_label})"
                )
            )
            options_list.append(
                selector.SelectOptionDict(
                    value=f"remove_{i}", label=f"Remove: {name}"
                )
            )
        options_list.append(
            selector.SelectOptionDict(value="continue", label="Continue")
        )

        return self.async_show_form(
            step_id="dump_loads",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="continue"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options_list,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={"count": str(len(loads))},
        )

    async def async_step_dump_load_type(self, user_input=None):
        """Pick manual vs. sensor for a new dump load."""
        if user_input is not None:
            if user_input[CONF_DUMP_LOAD_TYPE] == DUMP_LOAD_TYPE_SENSOR:
                return await self.async_step_dump_load_sensor()
            return await self.async_step_dump_load_manual()

        return self.async_show_form(
            step_id="dump_load_type",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DUMP_LOAD_TYPE, default=DUMP_LOAD_TYPE_MANUAL
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=DUMP_LOAD_TYPE_MANUAL,
                                    label="Manual entry (avg kW + window)",
                                ),
                                selector.SelectOptionDict(
                                    value=DUMP_LOAD_TYPE_SENSOR,
                                    label="Power sensor (auto-track)",
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_dump_load_manual(self, user_input=None):
        """Simple manual: name, avg_kw, start/end hour, optional advanced toggle."""
        existing = self._get_editing_load()

        if user_input is not None:
            advanced = user_input.pop(CONF_DUMP_LOAD_ADVANCED, False)
            self._pending_dump_load = {
                CONF_DUMP_LOAD_NAME: user_input[CONF_DUMP_LOAD_NAME],
                CONF_DUMP_LOAD_TYPE: DUMP_LOAD_TYPE_MANUAL,
                CONF_DUMP_LOAD_AVG_KW: user_input[CONF_DUMP_LOAD_AVG_KW],
                CONF_DUMP_LOAD_START_HOUR: user_input[CONF_DUMP_LOAD_START_HOUR],
                CONF_DUMP_LOAD_END_HOUR: user_input[CONF_DUMP_LOAD_END_HOUR],
            }
            if advanced:
                if existing.get(CONF_DUMP_LOAD_HOURLY_PROFILE):
                    self._pending_dump_load[CONF_DUMP_LOAD_HOURLY_PROFILE] = list(
                        existing[CONF_DUMP_LOAD_HOURLY_PROFILE]
                    )
                return await self.async_step_dump_load_manual_advanced()
            self._commit_dump_load(self._pending_dump_load)
            return await self.async_step_dump_loads()

        return self.async_show_form(
            step_id="dump_load_manual",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DUMP_LOAD_NAME,
                        default=existing.get(CONF_DUMP_LOAD_NAME, ""),
                    ): str,
                    vol.Required(
                        CONF_DUMP_LOAD_AVG_KW,
                        default=existing.get(
                            CONF_DUMP_LOAD_AVG_KW, DEFAULT_DUMP_LOAD_AVG_KW
                        ),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
                    vol.Required(
                        CONF_DUMP_LOAD_START_HOUR,
                        default=existing.get(
                            CONF_DUMP_LOAD_START_HOUR, DEFAULT_DUMP_LOAD_START_HOUR
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                    vol.Required(
                        CONF_DUMP_LOAD_END_HOUR,
                        default=existing.get(
                            CONF_DUMP_LOAD_END_HOUR, DEFAULT_DUMP_LOAD_END_HOUR
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                    vol.Required(
                        CONF_DUMP_LOAD_ADVANCED,
                        default=bool(existing.get(CONF_DUMP_LOAD_HOURLY_PROFILE)),
                    ): bool,
                }
            ),
        )

    async def async_step_dump_load_manual_advanced(self, user_input=None):
        """24 hourly kW values (overrides simple window when present)."""
        pending = self._pending_dump_load or {}
        existing_profile: list[float] | None = pending.get(CONF_DUMP_LOAD_HOURLY_PROFILE)
        if not existing_profile:
            avg = float(pending.get(CONF_DUMP_LOAD_AVG_KW, DEFAULT_DUMP_LOAD_AVG_KW))
            sh = int(pending.get(CONF_DUMP_LOAD_START_HOUR, DEFAULT_DUMP_LOAD_START_HOUR))
            eh = int(pending.get(CONF_DUMP_LOAD_END_HOUR, DEFAULT_DUMP_LOAD_END_HOUR))
            existing_profile = [avg if (sh <= h < eh) else 0.0 for h in range(24)]

        if user_input is not None:
            profile = [
                float(user_input.get(f"hour_{h}", 0.0)) for h in range(24)
            ]
            assert self._pending_dump_load is not None
            self._pending_dump_load[CONF_DUMP_LOAD_HOURLY_PROFILE] = profile
            self._commit_dump_load(self._pending_dump_load)
            return await self.async_step_dump_loads()

        schema_dict: dict = {}
        for h in range(24):
            schema_dict[
                vol.Required(f"hour_{h}", default=existing_profile[h])
            ] = vol.All(vol.Coerce(float), vol.Range(min=0.0))

        return self.async_show_form(
            step_id="dump_load_manual_advanced",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_dump_load_sensor(self, user_input=None):
        """Sensor-based dump load: name + power entity (W)."""
        existing = self._get_editing_load()

        if user_input is not None:
            self._commit_dump_load(
                {
                    CONF_DUMP_LOAD_NAME: user_input[CONF_DUMP_LOAD_NAME],
                    CONF_DUMP_LOAD_TYPE: DUMP_LOAD_TYPE_SENSOR,
                    CONF_DUMP_LOAD_POWER_ENTITY: user_input[
                        CONF_DUMP_LOAD_POWER_ENTITY
                    ],
                }
            )
            return await self.async_step_dump_loads()

        schema: dict = {
            vol.Required(
                CONF_DUMP_LOAD_NAME, default=existing.get(CONF_DUMP_LOAD_NAME, "")
            ): str,
        }
        if existing.get(CONF_DUMP_LOAD_POWER_ENTITY):
            schema[
                vol.Required(
                    CONF_DUMP_LOAD_POWER_ENTITY,
                    default=existing[CONF_DUMP_LOAD_POWER_ENTITY],
                )
            ] = ENTITY_SELECTOR
        else:
            schema[vol.Required(CONF_DUMP_LOAD_POWER_ENTITY)] = ENTITY_SELECTOR

        return self.async_show_form(
            step_id="dump_load_sensor",
            data_schema=vol.Schema(schema),
        )


class SunriseSocForecastConfigFlow(
    DumpLoadFlowMixin, config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for Sunrise SoC Forecast."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Main battery configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_backup()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAIN_SOC_ENTITY): ENTITY_SELECTOR,
                    vol.Required(CONF_MAIN_POWER_ENTITY): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_MAIN_CAPACITY, default=DEFAULT_MAIN_CAPACITY
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_MAIN_FLOOR, default=DEFAULT_MAIN_FLOOR
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Optional(
                        CONF_MAIN_INVERTER_EFFICIENCY, default=DEFAULT_MAIN_INVERTER_EFFICIENCY
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                    vol.Optional(CONF_GRID_POWER_ENTITY): ENTITY_SELECTOR,
                }
            ),
        )

    async def async_step_backup(self, user_input=None):
        """Step 2: Backup battery toggle."""
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_BACKUP_ENABLED, False):
                return await self.async_step_backup_details()
            return await self.async_step_dump_loads()

        return self.async_show_form(
            step_id="backup",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BACKUP_ENABLED, default=False): bool,
                }
            ),
        )

    async def async_step_backup_details(self, user_input=None):
        """Step 2b: Backup battery details."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_dump_loads()

        return self.async_show_form(
            step_id="backup_details",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BACKUP_SOC_ENTITY): ENTITY_SELECTOR,
                    vol.Required(CONF_BACKUP_DISCHARGE_ENTITY): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_BACKUP_CAPACITY, default=DEFAULT_BACKUP_CAPACITY
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_BACKUP_FLOOR, default=DEFAULT_BACKUP_FLOOR
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Required(
                        CONF_BACKUP_DISCHARGE_KW, default=DEFAULT_BACKUP_DISCHARGE_KW
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_BACKUP_ACTIVATION_HOUR,
                        default=DEFAULT_BACKUP_ACTIVATION_HOUR,
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
                    vol.Required(
                        CONF_BACKUP_MODE, default=BACKUP_MODE_ALWAYS
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=BACKUP_MODE_ALWAYS, label="Always discharge nightly"),
                                selector.SelectOptionDict(value=BACKUP_MODE_TARGET, label="Only if needed to reach target SoC"),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_BACKUP_CHARGE_EFFICIENCY, default=DEFAULT_BACKUP_CHARGE_EFFICIENCY
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                    vol.Optional(
                        CONF_BACKUP_DISCHARGE_EFFICIENCY, default=DEFAULT_BACKUP_DISCHARGE_EFFICIENCY
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                }
            ),
        )

    def _find_solar_integrations(self) -> list[selector.SelectOptionDict]:
        """Find installed solar forecast integrations."""
        options = []
        for entry in self.hass.config_entries.async_entries():
            if entry.domain in SOLAR_DOMAINS:
                label = f"{entry.title} ({entry.domain})"
                options.append(
                    selector.SelectOptionDict(value=entry.entry_id, label=label)
                )
        options.append(
            selector.SelectOptionDict(value=SOLAR_SOURCE_MANUAL, label="Manual entity selection")
        )
        return options

    async def async_step_solar_source(self, user_input=None):
        """Step 3: Solar forecast source selection."""
        if user_input is not None:
            selected = user_input.get(CONF_SOLAR_CONFIG_ENTRY, SOLAR_SOURCE_MANUAL)
            if selected == SOLAR_SOURCE_MANUAL:
                self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
                return await self.async_step_solcast()

            # Auto-discover entities from selected integration
            entry = self.hass.config_entries.async_get_entry(selected)
            if entry:
                self._data[CONF_SOLAR_SOURCE] = SOLAR_DOMAINS.get(entry.domain, SOLAR_SOURCE_MANUAL)
                self._data[CONF_SOLAR_CONFIG_ENTRY] = selected

            discovered = discover_solar_entities(self.hass, selected)
            if not discovered.get("today") and not discovered.get("tomorrow"):
                # Discovery failed — fall back to manual
                _LOGGER.warning("Solar entity discovery found no forecast entities, falling back to manual")
                self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
                return await self.async_step_solcast()

            # Map discovered entities to config keys
            role_to_conf = {
                "remaining": CONF_SOLAR_ENTITY_REMAINING,
                "today": CONF_SOLAR_ENTITY_TODAY,
                "tomorrow": CONF_SOLAR_ENTITY_TOMORROW,
                "day_3": CONF_SOLAR_ENTITY_DAY_3,
                "day_4": CONF_SOLAR_ENTITY_DAY_4,
                "day_5": CONF_SOLAR_ENTITY_DAY_5,
                "day_6": CONF_SOLAR_ENTITY_DAY_6,
                "day_7": CONF_SOLAR_ENTITY_DAY_7,
            }
            for role, entity_id in discovered.items():
                conf_key = role_to_conf.get(role)
                if conf_key:
                    self._data[conf_key] = entity_id

            # Also set legacy Solcast keys for backward compatibility
            if discovered.get("remaining"):
                self._data[CONF_SOLCAST_REMAINING] = discovered["remaining"]
            if discovered.get("today"):
                self._data[CONF_SOLCAST_FORECAST_TODAY] = discovered["today"]
            if discovered.get("tomorrow"):
                self._data[CONF_SOLCAST_TOMORROW] = discovered["tomorrow"]
            for d in range(3, 8):
                role = f"day_{d}"
                conf = {3: CONF_SOLCAST_DAY_3, 4: CONF_SOLCAST_DAY_4, 5: CONF_SOLCAST_DAY_5,
                        6: CONF_SOLCAST_DAY_6, 7: CONF_SOLCAST_DAY_7}.get(d)
                if conf and discovered.get(role):
                    self._data[conf] = discovered[role]

            _LOGGER.info("Solar discovery found: %s", {k: v for k, v in discovered.items()})
            return await self.async_step_options()

        solar_options = self._find_solar_integrations()

        # If only manual option available, skip straight to manual
        if len(solar_options) <= 1:
            self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
            return await self.async_step_solcast()

        return self.async_show_form(
            step_id="solar_source",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOLAR_CONFIG_ENTRY): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=solar_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_solcast(self, user_input=None):
        """Step 3b: Manual Solcast entity configuration (fallback)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_options()

        return self.async_show_form(
            step_id="solcast",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOLCAST_REMAINING): ENTITY_SELECTOR,
                    vol.Optional(CONF_SOLCAST_FORECAST_TODAY): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_TOMORROW): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_DAY_3): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_DAY_4): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_DAY_5): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_DAY_6): ENTITY_SELECTOR,
                    vol.Required(CONF_SOLCAST_DAY_7): ENTITY_SELECTOR,
                }
            ),
        )

    async def async_step_options(self, user_input=None):
        """Step 4: Forecast options and consumption defaults."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Sunrise SoC Forecast",
                data=self._data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FORECAST_DAYS, default=DEFAULT_FORECAST_DAYS
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=7)),
                    vol.Required(
                        CONF_TARGET_SOC, default=DEFAULT_TARGET_SOC
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Required(
                        CONF_DEFAULT_DAILY, default=DEFAULT_DAILY_CONSUMPTION
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_DEFAULT_OVERNIGHT, default=DEFAULT_OVERNIGHT_CONSUMPTION
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_GUARD_THRESHOLD, default=DEFAULT_GUARD_THRESHOLD
                    ): vol.Coerce(float),
                }
            ),
        )

    @classmethod
    @callback
    def async_get_options_flow(cls, config_entry):
        """Get the options flow."""
        return SunriseSocOptionsFlow()


class SunriseSocOptionsFlow(DumpLoadFlowMixin, config_entries.OptionsFlow):
    """Section-based options flow with a menu landing page.

    Existing users land on a menu and edit one section at a time, instead
    of walking through every step linearly.
    """

    def __init__(self) -> None:
        self._data: dict = {}

    def _get_data(self) -> dict:
        """Existing entry values overlaid with edits in progress."""
        return {
            **self.config_entry.data,
            **self.config_entry.options,
            **self._data,
        }

    def _get_existing_dump_loads(self) -> list[dict]:
        return list(self._get_data().get(CONF_DUMP_LOADS, []))

    def _save_and_exit(self):
        """Persist the current section's edits, preserving other sections."""
        merged = {**self.config_entry.options, **self._data}
        return self.async_create_entry(title="", data=merged)

    async def _dump_loads_done(self):
        return self._save_and_exit()

    async def async_step_init(self, user_input=None):
        """Menu: pick a section to edit."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "main_battery",
                "backup",
                "dump_loads",
                "solar_source",
                "forecast_options",
            ],
        )

    async def async_step_main_battery(self, user_input=None):
        """Edit main battery settings."""
        if user_input is not None:
            self._data.update(user_input)
            return self._save_and_exit()

        data = self._get_data()
        return self.async_show_form(
            step_id="main_battery",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MAIN_SOC_ENTITY,
                        default=data.get(CONF_MAIN_SOC_ENTITY),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_MAIN_POWER_ENTITY,
                        default=data.get(CONF_MAIN_POWER_ENTITY),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_MAIN_CAPACITY,
                        default=data.get(CONF_MAIN_CAPACITY, DEFAULT_MAIN_CAPACITY),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_MAIN_FLOOR,
                        default=data.get(CONF_MAIN_FLOOR, DEFAULT_MAIN_FLOOR),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Optional(
                        CONF_MAIN_INVERTER_EFFICIENCY,
                        description={"suggested_value": data.get(CONF_MAIN_INVERTER_EFFICIENCY, DEFAULT_MAIN_INVERTER_EFFICIENCY)},
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                    vol.Optional(
                        CONF_GRID_POWER_ENTITY,
                        description={"suggested_value": data.get(CONF_GRID_POWER_ENTITY)},
                    ): ENTITY_SELECTOR,
                }
            ),
        )

    async def async_step_backup(self, user_input=None):
        """Toggle backup battery — branches to details or saves & exits."""
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_BACKUP_ENABLED, False):
                return await self.async_step_backup_details()
            return self._save_and_exit()

        data = self._get_data()
        return self.async_show_form(
            step_id="backup",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BACKUP_ENABLED,
                        default=data.get(CONF_BACKUP_ENABLED, False),
                    ): bool,
                }
            ),
        )

    async def async_step_backup_details(self, user_input=None):
        """Edit backup battery details."""
        if user_input is not None:
            self._data.update(user_input)
            return self._save_and_exit()

        data = self._get_data()
        return self.async_show_form(
            step_id="backup_details",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BACKUP_SOC_ENTITY,
                        default=data.get(CONF_BACKUP_SOC_ENTITY),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_BACKUP_DISCHARGE_ENTITY,
                        default=data.get(CONF_BACKUP_DISCHARGE_ENTITY),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_BACKUP_CAPACITY,
                        default=data.get(CONF_BACKUP_CAPACITY, DEFAULT_BACKUP_CAPACITY),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_BACKUP_FLOOR,
                        default=data.get(CONF_BACKUP_FLOOR, DEFAULT_BACKUP_FLOOR),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Required(
                        CONF_BACKUP_DISCHARGE_KW,
                        default=data.get(CONF_BACKUP_DISCHARGE_KW, DEFAULT_BACKUP_DISCHARGE_KW),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
                    vol.Required(
                        CONF_BACKUP_ACTIVATION_HOUR,
                        default=data.get(CONF_BACKUP_ACTIVATION_HOUR, DEFAULT_BACKUP_ACTIVATION_HOUR),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
                    vol.Required(
                        CONF_BACKUP_MODE,
                        default=data.get(CONF_BACKUP_MODE, BACKUP_MODE_ALWAYS),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=BACKUP_MODE_ALWAYS, label="Always discharge nightly"),
                                selector.SelectOptionDict(value=BACKUP_MODE_TARGET, label="Only if needed to reach target SoC"),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_BACKUP_CHARGE_EFFICIENCY,
                        description={"suggested_value": data.get(CONF_BACKUP_CHARGE_EFFICIENCY, DEFAULT_BACKUP_CHARGE_EFFICIENCY)},
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                    vol.Optional(
                        CONF_BACKUP_DISCHARGE_EFFICIENCY,
                        description={"suggested_value": data.get(CONF_BACKUP_DISCHARGE_EFFICIENCY, DEFAULT_BACKUP_DISCHARGE_EFFICIENCY)},
                    ): vol.All(vol.Coerce(float), vol.Range(min=50, max=100)),
                }
            ),
        )

    def _find_solar_integrations(self) -> list[selector.SelectOptionDict]:
        """Find installed solar forecast integrations."""
        options = []
        for entry in self.hass.config_entries.async_entries():
            if entry.domain in SOLAR_DOMAINS:
                label = f"{entry.title} ({entry.domain})"
                options.append(
                    selector.SelectOptionDict(value=entry.entry_id, label=label)
                )
        options.append(
            selector.SelectOptionDict(value=SOLAR_SOURCE_MANUAL, label="Manual entity selection")
        )
        return options

    async def async_step_solar_source(self, user_input=None):
        """Pick solar source — auto-discover or fall through to manual."""
        if user_input is not None:
            selected = user_input.get(CONF_SOLAR_CONFIG_ENTRY, SOLAR_SOURCE_MANUAL)
            if selected == SOLAR_SOURCE_MANUAL:
                self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
                return await self.async_step_solcast()

            entry = self.hass.config_entries.async_get_entry(selected)
            if entry:
                self._data[CONF_SOLAR_SOURCE] = SOLAR_DOMAINS.get(entry.domain, SOLAR_SOURCE_MANUAL)
                self._data[CONF_SOLAR_CONFIG_ENTRY] = selected

            discovered = discover_solar_entities(self.hass, selected)
            if not discovered.get("today") and not discovered.get("tomorrow"):
                _LOGGER.warning("Solar entity discovery found no forecast entities, falling back to manual")
                self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
                return await self.async_step_solcast()

            role_to_conf = {
                "remaining": CONF_SOLAR_ENTITY_REMAINING,
                "today": CONF_SOLAR_ENTITY_TODAY,
                "tomorrow": CONF_SOLAR_ENTITY_TOMORROW,
                "day_3": CONF_SOLAR_ENTITY_DAY_3,
                "day_4": CONF_SOLAR_ENTITY_DAY_4,
                "day_5": CONF_SOLAR_ENTITY_DAY_5,
                "day_6": CONF_SOLAR_ENTITY_DAY_6,
                "day_7": CONF_SOLAR_ENTITY_DAY_7,
            }
            for role, entity_id in discovered.items():
                conf_key = role_to_conf.get(role)
                if conf_key:
                    self._data[conf_key] = entity_id

            if discovered.get("remaining"):
                self._data[CONF_SOLCAST_REMAINING] = discovered["remaining"]
            if discovered.get("today"):
                self._data[CONF_SOLCAST_FORECAST_TODAY] = discovered["today"]
            if discovered.get("tomorrow"):
                self._data[CONF_SOLCAST_TOMORROW] = discovered["tomorrow"]
            for d in range(3, 8):
                role = f"day_{d}"
                conf = {3: CONF_SOLCAST_DAY_3, 4: CONF_SOLCAST_DAY_4, 5: CONF_SOLCAST_DAY_5,
                        6: CONF_SOLCAST_DAY_6, 7: CONF_SOLCAST_DAY_7}.get(d)
                if conf and discovered.get(role):
                    self._data[conf] = discovered[role]

            _LOGGER.info("Solar discovery found: %s", {k: v for k, v in discovered.items()})
            return self._save_and_exit()

        solar_options = self._find_solar_integrations()

        if len(solar_options) <= 1:
            self._data[CONF_SOLAR_SOURCE] = SOLAR_SOURCE_MANUAL
            return await self.async_step_solcast()

        data = self._get_data()
        current = data.get(CONF_SOLAR_CONFIG_ENTRY, SOLAR_SOURCE_MANUAL)

        return self.async_show_form(
            step_id="solar_source",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOLAR_CONFIG_ENTRY,
                        default=current,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=solar_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_solcast(self, user_input=None):
        """Manual solar entity selection (fallback)."""
        if user_input is not None:
            self._data.update(user_input)
            return self._save_and_exit()

        data = self._get_data()
        return self.async_show_form(
            step_id="solcast",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SOLCAST_REMAINING,
                        default=data.get(CONF_SOLCAST_REMAINING),
                    ): ENTITY_SELECTOR,
                    vol.Optional(
                        CONF_SOLCAST_FORECAST_TODAY,
                        description={"suggested_value": data.get(CONF_SOLCAST_FORECAST_TODAY)},
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_TOMORROW,
                        default=data.get(CONF_SOLCAST_TOMORROW),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_DAY_3,
                        default=data.get(CONF_SOLCAST_DAY_3),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_DAY_4,
                        default=data.get(CONF_SOLCAST_DAY_4),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_DAY_5,
                        default=data.get(CONF_SOLCAST_DAY_5),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_DAY_6,
                        default=data.get(CONF_SOLCAST_DAY_6),
                    ): ENTITY_SELECTOR,
                    vol.Required(
                        CONF_SOLCAST_DAY_7,
                        default=data.get(CONF_SOLCAST_DAY_7),
                    ): ENTITY_SELECTOR,
                }
            ),
        )

    async def async_step_forecast_options(self, user_input=None):
        """Edit forecast options and fallback consumption defaults."""
        if user_input is not None:
            self._data.update(user_input)
            return self._save_and_exit()

        data = self._get_data()
        return self.async_show_form(
            step_id="forecast_options",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FORECAST_DAYS,
                        default=data.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=7)),
                    vol.Required(
                        CONF_TARGET_SOC,
                        default=data.get(CONF_TARGET_SOC, DEFAULT_TARGET_SOC),
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Required(
                        CONF_DEFAULT_DAILY,
                        default=data.get(CONF_DEFAULT_DAILY, DEFAULT_DAILY_CONSUMPTION),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_DEFAULT_OVERNIGHT,
                        default=data.get(CONF_DEFAULT_OVERNIGHT, DEFAULT_OVERNIGHT_CONSUMPTION),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_GUARD_THRESHOLD,
                        default=data.get(CONF_GUARD_THRESHOLD, DEFAULT_GUARD_THRESHOLD),
                    ): vol.Coerce(float),
                }
            ),
        )
