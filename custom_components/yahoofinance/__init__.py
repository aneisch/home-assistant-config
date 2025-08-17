"""The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

from __future__ import annotations

import contextlib
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import CONF_SCAN_INTERVAL, SERVICE_RELOAD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import discovery, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_DECIMAL_PLACES,
    CONF_INCLUDE_DIVIDEND_VALUES,
    CONF_INCLUDE_FIFTY_DAY_VALUES,
    CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
    CONF_INCLUDE_POST_VALUES,
    CONF_INCLUDE_PRE_VALUES,
    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    CONF_NO_UNIT,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    CONF_TARGET_CURRENCY,
    DEFAULT_CONF_DECIMAL_PLACES,
    DEFAULT_CONF_INCLUDE_DIVIDEND_VALUES,
    DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
    DEFAULT_CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
    DEFAULT_CONF_INCLUDE_POST_VALUES,
    DEFAULT_CONF_INCLUDE_PRE_VALUES,
    DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
    DEFAULT_CONF_NO_UNIT,
    DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    DEFAULT_CONF_SHOW_TRENDING_ICON,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HASS_DATA_CONFIG,
    HASS_DATA_COORDINATORS,
    LOGGER,
    MANUAL_SCAN_INTERVAL,
    MAX_LINE_SIZE,
    MINIMUM_SCAN_INTERVAL,
    SERVICE_REFRESH,
)
from .coordinator import CrumbCoordinator, YahooSymbolUpdateCoordinator
from .dataclasses import SymbolDefinition

BASIC_SYMBOL_SCHEMA = vol.All(cv.string, vol.Upper)


def minimum_scan_interval(value: timedelta) -> timedelta:
    """Validate scan_interval is the minimum value."""
    if value < MINIMUM_SCAN_INTERVAL:
        raise vol.Invalid("Scan interval should be at least 30 seconds")
    return value


MANUAL_SCAN_INTERVAL_SCHEMA = vol.All(vol.Lower, MANUAL_SCAN_INTERVAL)
CUSTOM_SCAN_INTERVAL_SCHEMA = vol.All(cv.time_period, minimum_scan_interval)
SCAN_INTERVAL_SCHEMA = vol.Any(MANUAL_SCAN_INTERVAL_SCHEMA, CUSTOM_SCAN_INTERVAL_SCHEMA)

COMPLEX_SYMBOL_SCHEMA = vol.All(
    dict,
    vol.Schema(
        {
            vol.Required("symbol"): BASIC_SYMBOL_SCHEMA,
            vol.Optional(CONF_TARGET_CURRENCY): BASIC_SYMBOL_SCHEMA,
            vol.Optional(CONF_SCAN_INTERVAL): SCAN_INTERVAL_SCHEMA,
            vol.Optional(CONF_NO_UNIT, default=DEFAULT_CONF_NO_UNIT): cv.boolean,
        }
    ),
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SYMBOLS): vol.All(
                    cv.ensure_list,
                    [vol.Any(BASIC_SYMBOL_SCHEMA, COMPLEX_SYMBOL_SCHEMA)],
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): SCAN_INTERVAL_SCHEMA,
                vol.Optional(CONF_TARGET_CURRENCY): vol.All(cv.string, vol.Upper),
                vol.Optional(
                    CONF_SHOW_TRENDING_ICON, default=DEFAULT_CONF_SHOW_TRENDING_ICON
                ): cv.boolean,
                vol.Optional(
                    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
                    default=DEFAULT_CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
                ): cv.boolean,
                vol.Optional(
                    CONF_DECIMAL_PLACES, default=DEFAULT_CONF_DECIMAL_PLACES
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_INCLUDE_FIFTY_DAY_VALUES,
                    default=DEFAULT_CONF_INCLUDE_FIFTY_DAY_VALUES,
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_POST_VALUES, default=DEFAULT_CONF_INCLUDE_POST_VALUES
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_PRE_VALUES, default=DEFAULT_CONF_INCLUDE_PRE_VALUES
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
                    default=DEFAULT_CONF_INCLUDE_TWO_HUNDRED_DAY_VALUES,
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
                    default=DEFAULT_CONF_INCLUDE_FIFTY_TWO_WEEK_VALUES,
                ): cv.boolean,
                vol.Optional(
                    CONF_INCLUDE_DIVIDEND_VALUES,
                    default=DEFAULT_CONF_INCLUDE_DIVIDEND_VALUES,
                ): cv.boolean,
            }
        )
    },
    # The complete HA configuration is passed down to`async_setup`, allow the extra keys.
    extra=vol.ALLOW_EXTRA,
)


def normalize_input_symbols(defined_symbols: list) -> list[SymbolDefinition]:
    """Normalize input and remove duplicates."""
    symbols = set()
    symbol_definitions: list[SymbolDefinition] = []

    for value in defined_symbols:
        if isinstance(value, str):
            if value not in symbols:
                symbols.add(value)
                symbol_definitions.append(SymbolDefinition(value))
        else:
            symbol = value["symbol"]
            if symbol not in symbols:
                symbols.add(symbol)
                symbol_definitions.append(
                    SymbolDefinition(
                        symbol,
                        target_currency=value.get(CONF_TARGET_CURRENCY),
                        scan_interval=value.get(CONF_SCAN_INTERVAL),
                        no_unit=value.get(CONF_NO_UNIT),
                    )
                )

    return symbol_definitions


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the component."""

    await _async_process_yaml(hass, config)

    async def handle_refresh_symbols(_call: ServiceCall) -> None:
        """Refresh symbol data."""
        LOGGER.info("Processing refresh_symbols")

        # Always use latest coordinators to handle config reload
        coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = hass.data[DOMAIN][
            HASS_DATA_COORDINATORS
        ]
        if coordinators:
            for coordinator in coordinators.values():
                await coordinator.async_refresh()

    async def _async_reload_service_handler(service: ServiceCall) -> None:
        """Handle reload service call."""
        reload_config = None
        with contextlib.suppress(HomeAssistantError):
            reload_config = await async_integration_yaml_config(hass, DOMAIN)
        if reload_config is None:
            return

        _remove_all_existing_symbols(hass)
        await _async_process_yaml(hass, reload_config)

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh_symbols)
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _async_reload_service_handler)
    return True


async def _async_process_yaml(hass: HomeAssistant, config: ConfigType) -> None:
    """Process YAML configuration."""
    domain_config = config.get(DOMAIN, {})
    defined_symbols = domain_config.get(CONF_SYMBOLS, [])

    symbol_definitions: list[SymbolDefinition]
    symbol_definitions = normalize_input_symbols(defined_symbols)
    domain_config[CONF_SYMBOLS] = symbol_definitions

    global_scan_interval = domain_config.get(CONF_SCAN_INTERVAL)

    # Populate parsed value into domain_config
    domain_config[CONF_SCAN_INTERVAL] = global_scan_interval

    # Group symbols by scan_interval
    symbols_by_scan_interval: dict[timedelta, list[str]] = {}
    for symbol in symbol_definitions:
        # Use integration level scan_interval if none defined
        if symbol.scan_interval is None:
            symbol.scan_interval = global_scan_interval

        if symbol.scan_interval in symbols_by_scan_interval:
            symbols_by_scan_interval[symbol.scan_interval].append(symbol.symbol)
        else:
            symbols_by_scan_interval[symbol.scan_interval] = [symbol.symbol]

    LOGGER.info("Total %d unique scan intervals", len(symbols_by_scan_interval))

    # Pass down the config to platforms.
    hass.data[DOMAIN] = {
        HASS_DATA_CONFIG: domain_config,
    }

    async def _setup_coordinators(now=None) -> None:
        # Testing showed that the response header for initial request can up to 40KB
        websession = async_create_clientsession(
            hass, max_field_size=MAX_LINE_SIZE, max_line_size=MAX_LINE_SIZE
        )

        # Using a static instance to keep the last successful cookies.
        crumb_coordinator = CrumbCoordinator.get_static_instance(hass, websession)

        crumb = await crumb_coordinator.try_get_crumb_cookies()  # Get crumb first
        if crumb is None:
            delay = crumb_coordinator.retry_duration
            LOGGER.warning("Unable to get crumb, re-trying in %d seconds", delay)
            async_call_later(hass, delay, _setup_coordinators)
            return

        coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = {}
        for key_scan_interval, symbols in symbols_by_scan_interval.items():
            LOGGER.info(
                "Creating coordinator with scan_interval %s for symbols %s",
                key_scan_interval,
                symbols,
            )
            coordinator = YahooSymbolUpdateCoordinator(
                symbols, hass, key_scan_interval, crumb_coordinator, websession
            )
            coordinators[key_scan_interval] = coordinator

            LOGGER.info(
                "Requesting initial data from coordinator with update interval of %s",
                key_scan_interval,
            )
            await coordinator.async_refresh()

        # Pass down the coordinator to platforms.
        hass.data[DOMAIN][HASS_DATA_COORDINATORS] = coordinators

        for coordinator in coordinators.values():
            if not coordinator.last_update_success:
                LOGGER.debug(
                    "Coordinator did not report any data, requesting async_refresh"
                )
                hass.async_create_task(coordinator.async_request_refresh())

        hass.async_create_task(
            discovery.async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
        )

    await _setup_coordinators()


def convert_to_float(value) -> float | None:
    """Convert specified value to float."""
    try:
        return float(value)
    except:  # noqa: E722 pylint: disable=bare-except
        return None


def _remove_all_existing_symbols(hass: HomeAssistant) -> None:
    """Remove all exisiting symbols."""
    coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = hass.data[DOMAIN][
        HASS_DATA_COORDINATORS
    ]

    if not coordinators:
        return

    all_existing_symbols = []
    for coordinator in coordinators.values():
        all_existing_symbols.extend(coordinator.get_symbols())

    if not all_existing_symbols:
        return

    entity_registry = er.async_get(hass)

    for symbol in all_existing_symbols:
        existing_sensor_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, symbol
        )
        if existing_sensor_id:
            LOGGER.debug("Removing entity %s", existing_sensor_id)
            entity_registry.async_remove(existing_sensor_id)
