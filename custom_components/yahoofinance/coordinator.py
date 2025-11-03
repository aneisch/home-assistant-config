"""The Yahoo finance component.

https://github.com/iprak/yahoofinance
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
import re
from typing import Any, Final

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers import event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE,
    CONSENT_HOST,
    CRUMB_RETRY_DELAY,
    CRUMB_RETRY_DELAY_429,
    DATA_REGULAR_MARKET_PRICE,
    EVENT_DATA_UPDATED,
    GET_CRUMB_URL,
    INITIAL_REQUEST_HEADERS,
    INITIAL_URL,
    LOGGER,
    MANUAL_SCAN_INTERVAL,
    NUMERIC_DATA_DEFAULTS,
    NUMERIC_DATA_GROUPS,
    STRING_DATA_KEYS,
    TOO_MANY_CRUMB_RETRY_FAILURES_COUNT,
    TOO_MANY_CRUMB_RETRY_FAILURES_DELAY,
    USER_AGENTS_FOR_XHR,
    XHR_REQUEST_HEADERS,
)

REQUEST_TIMEOUT: Final = 10
DELAY_ASYNC_REQUEST_REFRESH: Final = 5
FAILURE_ASYNC_REQUEST_REFRESH: Final = 20


class CrumbCoordinator:
    """Class to gather crumb/cookie details."""

    _instance = None
    """Static instance of CrumbCoordinator."""

    preferred_user_agent = ""
    """The preferred (last successeful) user agent."""

    def __init__(self, hass: HomeAssistant, websession: aiohttp.ClientSession) -> None:
        """Initialize."""

        self.cookies: SimpleCookie[str] = None
        """Cookies for requests."""
        self.crumb: str | None = None
        """Crumb for requests."""
        self._hass = hass

        self.retry_duration = CRUMB_RETRY_DELAY
        """Crumb retry request delay."""

        self._crumb_retry_count = 0
        self._websession = websession

    @staticmethod
    def get_static_instance(
        hass: HomeAssistant, websession: aiohttp.ClientSession
    ) -> CrumbCoordinator:
        """Get the singleton static CrumbCoordinator instance."""
        if CrumbCoordinator._instance is None:
            CrumbCoordinator._instance = CrumbCoordinator(hass, websession)
        return CrumbCoordinator._instance

    def reset(self) -> None:
        """Reset crumb and cookies."""
        self.crumb = self.cookies = None

    async def try_get_crumb_cookies(self) -> str | None:
        """Try to get crumb and cookies for data requests."""

        consent_data = await self.initial_navigation(INITIAL_URL)
        if consent_data is None:  # Consent check failed
            return None

        if consent_data.need_consent:
            if not await self.process_consent(consent_data):
                return None

            data = await self.initial_navigation(consent_data.successful_consent_url)

            if data is None:  # Something went bad, we did get consent
                LOGGER.error("Post consent navigation failed")
                return None

            if data.need_consent:
                LOGGER.error("Yahoo reported needing consent even after we got it once")
                return None

        if self.cookies_missing():
            LOGGER.warning(
                "Attempting to get crumb but have no cookies, the operation might fail"
            )

        await self.try_crumb_page()
        return self.crumb

    async def initial_navigation(self, url: str) -> ConsentData | None:
        """Navigate to base page. This determines if consent is needed.

        Returns:
            None if consent check failed or the consent response

        """

        LOGGER.debug("Navigating to base page %s", url)

        try:
            async with self._websession.get(
                url,
                headers=INITIAL_REQUEST_HEADERS,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                LOGGER.debug("Response %d, URL: %s", response.status, response.url)

                if response.status != HTTPStatus.OK:
                    LOGGER.error(
                        "Failed to navigate to %s, status=%d, reason=%s",
                        url,
                        response.status,
                        response.reason,
                    )
                    return None

                # This request will return cookies only if consent is not needed
                if response.cookies:
                    self.cookies = response.cookies

                # https://guce.yahoo.com/consent?brandType=nonEu&gcrumb=eZ_Jbm0&done=https%3A%2F%2Ffinance.yahoo.com%2F
                if response.url.host.lower() == CONSENT_HOST:
                    LOGGER.info("Consent page %s detected", response.url)

                    return ConsentData(
                        need_consent=True,
                        consent_content=await response.text(),
                        consent_post_url=response.url,
                    )

                LOGGER.debug("No consent needed, have cookies=%s", bool(self.cookies))

        except TimeoutError as ex:
            LOGGER.error("Timed out accessing initial url. %s", ex)
        except aiohttp.ClientError as ex:
            LOGGER.error("Error accessing initial url. %s", ex)
        except Exception as ex:
            LOGGER.error("Unexpected error accessing initial url. %s", ex)

        return ConsentData()

    async def process_consent(self, consent_data: ConsentData) -> bool:
        """Process GDPR consent."""

        # websession = async_get_clientsession(self._hass)
        form_data = self.build_consent_form_data(consent_data.consent_content)
        LOGGER.debug("Posting consent %s", str(form_data))

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._websession.post(
                    consent_data.consent_post_url,
                    data=form_data,
                    headers=INITIAL_REQUEST_HEADERS,
                )

                # Sample responses
                # 302 https://guce.yahoo.com/copyConsent?sessionId=3_cc-session_0d6c4281-76f7-44ce-8783-6db9d4f39c40&lang=nb-NO
                # 302 https://finance.yahoo.com/?guccounter=1
                # 200

                if response.status != HTTPStatus.OK:
                    LOGGER.error(
                        "Failed to post consent %d, reason=%s",
                        response.status,
                        response.reason,
                    )
                    return False

                if response.cookies:
                    self.cookies = response.cookies

                consent_data.successful_consent_url = response.url

                LOGGER.debug(
                    "After consent processing, have cookies=%s", bool(self.cookies)
                )
                return True

        except TimeoutError as ex:
            LOGGER.error("Timed out processing consent. %s", ex)
        except aiohttp.ClientError as ex:
            LOGGER.error("Error accessing consent url. %s", ex)

        return False

    def cookies_missing(self) -> bool:
        """Check if we don't have any cookies."""
        return self.cookies is None or len(self.cookies) == 0

    async def try_crumb_page(self) -> str | None:
        """Try to get crumb from the end point."""

        LOGGER.info("Accessing crumb page")
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        last_status = 0

        for user_agent in USER_AGENTS_FOR_XHR:
            headers = {**XHR_REQUEST_HEADERS, "user-agent": user_agent}

            async with self._websession.get(
                GET_CRUMB_URL, headers=headers, timeout=timeout, cookies=self.cookies
            ) as response:
                last_status = response.status

                if last_status == HTTPStatus.OK:
                    self.preferred_user_agent = user_agent

                    self.crumb = await response.text()
                    if not self.crumb:
                        LOGGER.error("No crumb reported")

                    LOGGER.info("Crumb page reported %s", self.crumb)
                    self._crumb_retry_count = 0
                    return self.crumb

                # Try next user-agent for 429, stop trying for any other failures
                if last_status == 429:
                    LOGGER.info(
                        "Crumb request responded with status 429 for '%s', re-trying with different agent",
                        user_agent,
                    )
                else:
                    LOGGER.error(
                        "Crumb request responded with status=%d, reason=%s",
                        last_status,
                        response.reason,
                    )

                    break

        self._crumb_retry_count = self._crumb_retry_count + 1

        if self._crumb_retry_count > TOO_MANY_CRUMB_RETRY_FAILURES_COUNT:
            self.retry_duration = TOO_MANY_CRUMB_RETRY_FAILURES_DELAY
            LOGGER.info(
                "Too many crumb failures, will retry after %d seconds",
                self.retry_duration,
            )

            self._crumb_retry_count = 0
        else:
            if last_status == 429:
                # Ideally we would want to use the seconds passed back in the header
                # for 429 but there seems to be no such value.
                self.retry_duration = CRUMB_RETRY_DELAY_429
            else:
                self.retry_duration = CRUMB_RETRY_DELAY

            LOGGER.info(
                "Crumb failure, will retry after %d seconds",
                self.retry_duration,
            )

        return None

    # async def parse_crumb_from_content(self, content: str) -> str:
    #     """Parse and update crumb from response content."""

    #     LOGGER.debug("Parsing crumb from content (length: %d)", len(content))

    #     start_pos = content.find('"crumb":"')
    #     LOGGER.debug("Start position: %d", start_pos)
    #     end_pos = -1

    #     if start_pos != -1:
    #         start_pos = start_pos + 9
    #         end_pos = content.find('"', start_pos + 10)
    #         LOGGER.debug("End position: %d", end_pos)
    #         if end_pos != -1:
    #             self.crumb = (
    #                 content[start_pos:end_pos]
    #                 .encode()
    #                 .decode("unicode_escape")
    #             )

    #     # Crumb was not located
    #     if not self.crumb:
    #         LOGGER.info(
    #             "Crumb not found, start position: %d, ending position: %d. Refer to YahooFinanceCrumbContent.log in the config folder.",
    #             start_pos,
    #             end_pos,
    #         )

    #         if LOGGER.isEnabledFor(logging.INFO):
    #             await self._hass.async_add_executor_job(
    #                 write_utf8_file,
    #                 self._hass.config.path("YahooFinanceCrumbContent.log"),
    #                 content,
    #             )

    def build_consent_form_data(self, content: str) -> dict[str, str]:
        """Build consent form data from response content."""
        pattern = r'<input.*?type="hidden".*?name="(.*?)".*?value="(.*?)".*?>'
        matches = re.findall(pattern, content)
        basic_data = {"reject": "reject"}  # From "Reject" submit button
        additional_data = dict(matches)
        return {**basic_data, **additional_data}


class YahooSymbolUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Yahoo finance data update coordinator."""

    @staticmethod
    def parse_symbol_data(symbol_data: dict) -> dict[str, any]:
        """Return data pieces which we care about, use 0 for missing numeric values."""
        data = {}

        # get() ensures that we have an entry in symbol_data.
        for data_group in NUMERIC_DATA_GROUPS.values():
            for value in data_group:
                key = value[0]

                # Default value for most missing numeric keys is 0
                default_value = NUMERIC_DATA_DEFAULTS.get(key, 0)

                data[key] = symbol_data.get(key, default_value)

        for key in STRING_DATA_KEYS:
            data[key] = symbol_data.get(key)

        return data

    @staticmethod
    def fix_conversion_symbol(symbol: str, symbol_data: any) -> str:
        """Fix the conversion symbol from data."""

        if symbol is None or symbol == "" or not symbol.endswith("=X"):
            return symbol

        # Data analysis showed that data for conversion symbol has 'shortName': 'USD/EUR'
        short_name = symbol_data["shortName"] or ""
        from_to = short_name.split("/")
        if len(from_to) != 2:
            return symbol

        from_currency = from_to[0]
        to_currency = from_to[1]
        if from_currency == "" or to_currency == "":
            return symbol

        conversion_symbol = f"{from_currency}{to_currency}=X"

        if conversion_symbol != symbol:
            LOGGER.info(
                "Conversion symbol updated to %s from %s", conversion_symbol, symbol
            )

        return conversion_symbol

    def __init__(
        self,
        symbols: list[str],
        hass: HomeAssistant,
        update_interval: timedelta,
        cc: CrumbCoordinator,
        webSession: aiohttp.ClientSession,
    ) -> None:
        """Initialize."""
        self._symbols = symbols
        self.data = None
        self.loop = hass.loop
        self.websession = webSession
        self._failure_update_interval = timedelta(seconds=FAILURE_ASYNC_REQUEST_REFRESH)
        self._cc = cc

        if isinstance(update_interval, str) and update_interval == MANUAL_SCAN_INTERVAL:
            update_interval = None

        self._defined_update_interval = update_interval

        super().__init__(
            hass,
            LOGGER,
            name="YahooSymbolUpdateCoordinator",
            update_interval=update_interval,
        )

    def get_symbols(self) -> list[str]:
        """Return symbols tracked by the coordinator."""
        return self._symbols

    async def _async_request_refresh_later(self, _now):
        """Request async_request_refresh."""
        await self.async_request_refresh()

    def add_symbol(self, symbol: str) -> bool:
        """Add symbol to the symbol list."""
        if symbol not in self._symbols:
            self._symbols.append(symbol)

            # Request a refresh to get data for the missing symbol.
            # This would have been called while data for sensor was being parsed.
            # async_request_refresh has debouncing built into it, so multiple calls
            # to add_symbol will still resut in single refresh.
            event.async_call_later(
                self.hass,
                DELAY_ASYNC_REQUEST_REFRESH,
                self._async_request_refresh_later,
            )

            LOGGER.info(
                "Added %s and requested update in %d seconds",
                symbol,
                DELAY_ASYNC_REQUEST_REFRESH,
            )
            return True

        return False

    async def get_json(self) -> dict:
        """Get the JSON data."""

        url = await self.build_request_url()

        preferred_user_agent = self._cc.preferred_user_agent
        if preferred_user_agent:
            LOGGER.info(
                "Requesting data request with the preferred agent '%s'",
                preferred_user_agent,
            )

            [result_json, status] = await self._fetch_json(url, preferred_user_agent)

            if status == HTTPStatus.OK:
                return result_json

            if status == 429:
                LOGGER.info(
                    "Data request responded with status 429 for '%s', re-trying other agents",
                    preferred_user_agent,
                )

        for user_agent in USER_AGENTS_FOR_XHR:
            # Skip if we have already tried the agent
            if preferred_user_agent == user_agent:
                continue

            [result_json, status] = await self._fetch_json(url, user_agent)

            if status == HTTPStatus.OK:
                LOGGER.info("Successful data received for '%s'", user_agent)
                return result_json

            if status != 429:
                break

            LOGGER.info(
                "Data request responded with status 429 for '%s', re-trying with different agent",
                user_agent,
            )

        return None

    async def _fetch_json(self, url, user_agent) -> tuple[dict, int]:
        """Fetch JSON data with the specified user agent."""

        headers = {**XHR_REQUEST_HEADERS, "user-agent": user_agent}
        LOGGER.debug("Requesting data from '%s' with agent %s", url, user_agent)

        async with asyncio.timeout(REQUEST_TIMEOUT):
            response = await self.websession.get(
                url, headers=headers, cookies=self._cc.cookies
            )

            # Try next user-agent for 429
            if response.status == 429:
                return [None, 429]

            result_json = await response.json()

            if response.status == HTTPStatus.OK:
                return [result_json, response.status]

            # Sample errors:
            #   {'finance':{'result': None, 'error': {'code': 'Unauthorized', 'description': 'Invalid Crumb'}}}
            #   {'finance':{'result': None, 'error': {'code': 'Unauthorized', 'description': 'Invalid Cookie'}}}
            finance_error_code_tuple = (
                YahooSymbolUpdateCoordinator.get_finance_error_code(result_json)
            )

            if finance_error_code_tuple:
                (
                    finance_error_code,
                    finance_error_description,
                ) = finance_error_code_tuple

                LOGGER.info(
                    "Received status %d (%s %s) for %s",
                    response.status,
                    finance_error_code,
                    finance_error_description,
                    url,
                )

                # Reset crumb so that it gets recalculated
                if finance_error_code == "Unauthorized":
                    LOGGER.info("Resetting crumbs")
                    self._cc.reset()

            else:
                LOGGER.info(
                    "Received status %d for %s, result=%s",
                    response.status,
                    url,
                    result_json,
                )

        return [None, response.status]

    async def build_request_url(self) -> str:
        """Build the request url."""
        url = BASE + ",".join(self._symbols)

        crumb = self._cc.crumb
        if crumb is None:
            crumb = await self._cc.try_get_crumb_cookies()
        if crumb is not None:
            url = url + "&crumb=" + crumb

        return url

    @staticmethod
    def get_finance_error_code(error_json) -> tuple[str, str] | None:
        """Parse error code from the json."""
        if error_json:
            finance = error_json.get("finance")
            if finance:
                finance_error = finance.get("error")
                if finance_error:
                    return finance_error.get("code"), finance_error.get("description")

        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Return updated data if new JSON is valid.

        The exception will get properly handled in the caller (DataUpdateCoordinator.async_refresh)
        which also updates last_update_success. UpdateFailed is raised if JSON is invalid.
        """

        # Set update interval for failure and reset it later if everything was okay
        self.update_interval = self._failure_update_interval

        try:
            json = await self.get_json()
        except (TimeoutError, aiohttp.ClientError) as error:
            raise UpdateFailed(error) from error

        if json is None:
            raise UpdateFailed("No data received")

        if "quoteResponse" not in json:
            raise UpdateFailed("Data invalid, 'quoteResponse' not found.")

        quoteResponse = json["quoteResponse"]  # pylint: disable=invalid-name

        if "error" in quoteResponse:
            if quoteResponse["error"] is not None:
                raise UpdateFailed(quoteResponse["error"])

        if "result" not in quoteResponse:
            raise UpdateFailed("Data invalid, no 'result' found")

        result = quoteResponse["result"]
        if result is None:
            raise UpdateFailed("Data invalid, 'result' is None")

        (error_encountered, data) = self.process_json_result(result)

        # Restore the specified interval
        self.update_interval = self._defined_update_interval

        if error_encountered:
            LOGGER.info("Data = %s", result)
        else:
            LOGGER.debug("Data = %s", result)

        self.hass.bus.fire(EVENT_DATA_UPDATED, {"symbols": ",".join(self._symbols)})
        return data

    def process_json_result(self, result) -> tuple[bool, dict[str, Any]]:
        """Process json result and return (error status, updated data)."""

        # Using current data if available. If returned data is missing then we might be
        # able to use previous data.
        data = self.data or {}

        symbols = self._symbols.copy()
        error_encountered = False

        for symbol_data in result:
            symbol = symbol_data["symbol"]

            if symbol in symbols:
                symbols.remove(symbol)
            else:
                # Sometimes data for USDEUR=X just contains EUR=X, try to fix such
                # symbols. The source of truth is the symbol in the data since data
                # pieces could be out of order.
                fixed_symbol = self.fix_conversion_symbol(symbol, symbol_data)

                if fixed_symbol in symbols:
                    symbols.remove(fixed_symbol)
                    symbol = fixed_symbol
                else:
                    LOGGER.warning("Received %s not in symbol list", symbol)
                    error_encountered = True

            data[symbol] = self.parse_symbol_data(symbol_data)

            LOGGER.debug(
                "Updated %s to %s",
                symbol,
                data[symbol][DATA_REGULAR_MARKET_PRICE],
            )

        if len(symbols) > 0:
            LOGGER.warning("No data received for %s", symbols)
            error_encountered = True

        return (error_encountered, data)


@dataclass
class ConsentData:
    """Class for data related to GDPR consent."""

    consent_content: str = ""
    """Consent verification content"""
    consent_post_url: str = ""
    """Url from consent check where data is to be submitted"""
    successful_consent_url: str = ""
    """Url to navigate to after successful consent"""
    need_consent: bool = False
    """Consent is needed"""


def debug_log_response(response: aiohttp.ClientResponse, title: str) -> None:
    """Debug log the response."""
    LOGGER.debug("%s: %d, %s", title, response.status, response.reason)
