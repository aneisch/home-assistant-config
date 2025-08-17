"""A component which presents Yahoo Finance stock quotes.

https://github.com/iprak/yahoofinance
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import convert_to_float
from .const import (
    ATTR_CURRENCY_SYMBOL,
    ATTR_MARKET_STATE,
    ATTR_QUOTE_SOURCE_NAME,
    ATTR_QUOTE_TYPE,
    ATTR_SYMBOL,
    ATTR_TRENDING,
    ATTRIBUTION,
    CONF_DECIMAL_PLACES,
    CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT,
    CONF_SHOW_TRENDING_ICON,
    CONF_SYMBOLS,
    CURRENCY_CODES,
    DATA_CURRENCY_SYMBOL,
    DATA_FINANCIAL_CURRENCY,
    DATA_LONG_NAME,
    DATA_MARKET_STATE,
    DATA_QUOTE_SOURCE_NAME,
    DATA_QUOTE_TYPE,
    DATA_REGULAR_MARKET_PREVIOUS_CLOSE,
    DATA_REGULAR_MARKET_PRICE,
    DATA_SHORT_NAME,
    DATE_DATA_KEYS,
    DEFAULT_CURRENCY,
    DEFAULT_NUMERIC_DATA_GROUP,
    DOMAIN,
    HASS_DATA_CONFIG,
    HASS_DATA_COORDINATORS,
    LOGGER,
    NUMERIC_DATA_GROUPS,
    PERCENTAGE_DATA_KEYS_NEEDING_MULTIPLICATION,
    TIME_DATA_KEYS,
)
from .coordinator import YahooSymbolUpdateCoordinator
from .dataclasses import SymbolDefinition

ENTITY_ID_FORMAT = SENSOR_DOMAIN + "." + DOMAIN + "_{}"


async def async_setup_platform(
    hass: HomeAssistant,
    _config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    _discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the Yahoo Finance sensor platform."""

    coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = hass.data[DOMAIN][
        HASS_DATA_COORDINATORS
    ]
    domain_config = hass.data[DOMAIN][HASS_DATA_CONFIG]
    symbol_definitions: list[SymbolDefinition] = domain_config[CONF_SYMBOLS]

    # We don't know the currency of a symbol so can't added conversion symbols upfront

    sensors = [
        YahooFinanceSensor(
            hass, coordinators[symbol.scan_interval], symbol, domain_config
        )
        for symbol in symbol_definitions
    ]

    # We have already invoked async_refresh on coordinator, so don'tupdate_before_add
    async_add_entities(sensors, update_before_add=False)
    LOGGER.info("Entities added for %s", [item.symbol for item in symbol_definitions])


class YahooFinanceSensor(CoordinatorEntity, SensorEntity):
    """Represents a Yahoo finance entity."""

    # pylint: disable=too-many-instance-attributes
    _currency = DEFAULT_CURRENCY
    _icon = None
    _market_price = None
    _long_name = None
    _short_name: str | None = None
    _symbol: str
    _target_currency = None
    _original_currency = None
    _last_available_timer = None
    _waiting_on_conversion = False

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = None

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: YahooSymbolUpdateCoordinator,
        symbol_definition: SymbolDefinition,
        domain_config: dict,
    ) -> None:
        """Initialize the YahooFinance entity."""
        super().__init__(coordinator)

        # Entity.hass is only populated after async_add_entities, use local reference to hass
        self._hass = hass

        symbol = symbol_definition.symbol
        self._symbol = symbol
        self._show_trending_icon = domain_config[CONF_SHOW_TRENDING_ICON]
        self._show_currency_symbol_as_unit = domain_config[
            CONF_SHOW_CURRENCY_SYMBOL_AS_UNIT
        ]
        self._decimal_places = domain_config[CONF_DECIMAL_PLACES]
        self._previous_close = None
        self._target_currency = symbol_definition.target_currency
        self._no_unit = symbol_definition.no_unit

        self._unique_id = symbol
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, symbol, hass=hass)

        # _attr_extra_state_attributes is returned by extra_state_attributes
        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_CURRENCY_SYMBOL: None,
            ATTR_SYMBOL: symbol,
            ATTR_QUOTE_TYPE: None,
            ATTR_QUOTE_SOURCE_NAME: None,
            ATTR_MARKET_STATE: None,
        }

        # List of groups to include as attributes
        self._numeric_data_to_include = []

        # pylint: disable=consider-using-dict-items

        # Initialize all numeric attributes which we want to include to None
        for group, group_items in NUMERIC_DATA_GROUPS.items():
            # All optional features data items are excluded by default
            if group == DEFAULT_NUMERIC_DATA_GROUP or domain_config.get(group, False):
                for value in group_items:
                    self._numeric_data_to_include.append(value)

                    key = value[0]
                    self._attr_extra_state_attributes[key] = None

        # Delay initial data population to `available` which is called from `_async_write_ha_state`
        LOGGER.debug(
            "Created entity for target_currency=%s",
            self._target_currency,
        )

        self.update_properties()

    @staticmethod
    def safe_convert(value: float | None, conversion: float | None) -> float | None:
        """Return the converted value. The original value is returned if there is no conversion."""
        if value is None:
            return None
        if conversion is None:
            return value
        return value * conversion

    @staticmethod
    def convert_timestamp_to_datetime(date_timestamp, return_format) -> str | None:
        """Convert Epoch JSON element to datetime."""

        date_timestamp = convert_to_float(date_timestamp)
        if date_timestamp is None or date_timestamp == 0:
            return date_timestamp

        converted_date = datetime.fromtimestamp(
            date_timestamp, tz=dt_util.DEFAULT_TIME_ZONE
        )
        if return_format == "date":
            converted_date = converted_date.date()

        return converted_date.isoformat()

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self._short_name is not None:
            # In UK regions, shortName was reported to be the same as symbol.
            # Falling to longName if that is available in that case.
            if self._short_name.lower() == self._symbol.lower():
                if self._long_name is not None:
                    return self._long_name
            else:
                return self._short_name

        return self._symbol

    @property
    def native_value(self) -> StateType | date | datetime:
        """Return the value reported by the sensor."""
        return self._round(self._market_price)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor, if any."""
        if self._no_unit:
            return None

        currency = self._target_currency if self._target_currency else self._currency

        if self._show_currency_symbol_as_unit:
            return CURRENCY_CODES.get(currency.lower(), currency)

        return currency

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        value = (
            self._market_price is not None
            and super().available
            and not self._waiting_on_conversion
        )
        LOGGER.debug("%s available=%s", self._symbol, value)
        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_properties()
        super()._handle_coordinator_update()

    def _round(self, value: float | None) -> float | int | None:
        """Return formatted value based on decimal_places."""
        if value is None:
            return None

        if self._decimal_places < 0:
            return value
        if self._decimal_places == 0:
            return int(value)

        return round(value, self._decimal_places)

    def _find_symbol_data(self, symbol: str) -> any | None:
        """Find data for the specified symbol in all coordinators."""
        coordinators: dict[timedelta, YahooSymbolUpdateCoordinator] = self._hass.data[
            DOMAIN
        ][HASS_DATA_COORDINATORS]

        if coordinators:
            for coordinator in coordinators.values():
                data = coordinator.data
                if data is not None:
                    symbol_data = data.get(symbol)
                    if symbol_data is not None:
                        return symbol_data

        return None

    def _get_target_currency_conversion(self) -> float | None:
        value = None
        self._waiting_on_conversion = False

        if self._target_currency and self._original_currency:
            if self._target_currency == self._original_currency:
                LOGGER.info("%s No conversion necessary", self._symbol)
                return None

            conversion_symbol = (
                f"{self._original_currency}{self._target_currency}=X".upper()
            )

            # Locate conversion symbol in all coordinators
            symbol_data = self._find_symbol_data(conversion_symbol)

            if symbol_data is not None:
                value = symbol_data[DATA_REGULAR_MARKET_PRICE]
                LOGGER.debug("%s %s is %s", self._symbol, conversion_symbol, value)
            else:
                LOGGER.info(
                    "%s No data found for %s, symbol added to coordinator",
                    self._symbol,
                    conversion_symbol,
                )
                self._waiting_on_conversion = True

                # The conversion symbol is added to the current coordinator
                self.coordinator.add_symbol(conversion_symbol)

        return value

    def _update_original_currency(self, symbol_data) -> bool:
        """Update the original currency."""

        # Symbol currency does not change so calculate it only once
        if self._original_currency is not None:
            return

        # Prefer currency over financialCurrency, for foreign symbols financialCurrency
        # can represent the remote currency. But financialCurrency can also be None.
        financial_currency = symbol_data[DATA_FINANCIAL_CURRENCY]
        currency = symbol_data[DATA_CURRENCY_SYMBOL]

        LOGGER.debug(
            "%s currency=%s financialCurrency=%s",
            self._symbol,
            currency,
            financial_currency,
        )

        self._original_currency = currency or financial_currency or DEFAULT_CURRENCY

    def update_properties(self) -> None:
        """Update local fields. This is also used in unit testing."""

        data = self.coordinator.data
        if data is None:
            LOGGER.debug("%s Coordinator data is None", self._symbol)
            return

        symbol_data: dict = data.get(self._symbol)
        if symbol_data is None:
            LOGGER.debug("%s Symbol data is None", self._symbol)
            return

        self._update_original_currency(symbol_data)
        conversion = self._get_target_currency_conversion()

        self._short_name = symbol_data[DATA_SHORT_NAME]
        self._long_name = symbol_data[DATA_LONG_NAME]

        market_price = symbol_data[DATA_REGULAR_MARKET_PRICE]
        self._market_price = self.safe_convert(market_price, conversion)
        # _market_price gets rounded in the `state` getter.

        if conversion:
            LOGGER.info(
                "%s converted %s X %s = %s",
                self._symbol,
                market_price,
                conversion,
                self._market_price,
            )

        self._previous_close = self.safe_convert(
            symbol_data[DATA_REGULAR_MARKET_PREVIOUS_CLOSE], conversion
        )

        for value in self._numeric_data_to_include:
            key = value[0]
            attr_value = symbol_data[key]

            # Convert if currency value
            if value[1]:
                attr_value = self.safe_convert(attr_value, conversion)

            if key in PERCENTAGE_DATA_KEYS_NEEDING_MULTIPLICATION:
                attr_value = attr_value * 100

            self._attr_extra_state_attributes[key] = self._round(attr_value)

        # Add some other string attributes
        self._attr_extra_state_attributes[ATTR_QUOTE_TYPE] = symbol_data[
            DATA_QUOTE_TYPE
        ]
        self._attr_extra_state_attributes[ATTR_QUOTE_SOURCE_NAME] = symbol_data[
            DATA_QUOTE_SOURCE_NAME
        ]
        self._attr_extra_state_attributes[ATTR_MARKET_STATE] = symbol_data[
            DATA_MARKET_STATE
        ]

        for key in DATE_DATA_KEYS:
            if key in self._attr_extra_state_attributes:
                self._attr_extra_state_attributes[key] = (
                    self.convert_timestamp_to_datetime(
                        self._attr_extra_state_attributes[key], "date"
                    )
                )

        for key in TIME_DATA_KEYS:
            if key in self._attr_extra_state_attributes:
                self._attr_extra_state_attributes[key] = (
                    self.convert_timestamp_to_datetime(
                        self._attr_extra_state_attributes[key], "dateTime"
                    )
                )

        # Use target_currency if we have conversion data. Otherwise keep using the
        # currency from data.
        if conversion is not None:
            currency = self._target_currency or self._original_currency
        else:
            currency = self._original_currency

        self._currency = currency.upper()
        lower_currency = self._currency.lower()

        trending_state = self._calc_trending_state()

        # Fall back to currency based icon if there is no trending state
        if trending_state is not None:
            self._attr_extra_state_attributes[ATTR_TRENDING] = trending_state

            if self._show_trending_icon:
                self._icon = f"mdi:trending-{trending_state}"
            else:
                self._icon = f"mdi:currency-{lower_currency}"
        else:
            self._icon = f"mdi:currency-{lower_currency}"

        # If this one of the known currencies, then include the correct currency symbol.
        # Don't show $ as the CurrencySymbol even if we can't get one.
        self._attr_extra_state_attributes[ATTR_CURRENCY_SYMBOL] = CURRENCY_CODES.get(
            lower_currency
        )

    def _calc_trending_state(self) -> str | None:
        """Return the trending state for the symbol."""
        if self._market_price is None or self._previous_close is None:
            return None

        if self._market_price > self._previous_close:
            return "up"
        if self._market_price < self._previous_close:
            return "down"

        return "neutral"
