"""Persistent state for the Solcast integration.

Set during crashes and sensitive reloads to allow the integration to detect and respond to repeated failures.

When in a sensitive state, the integration will not rely on cached sites data. If a sites load failure occurs
while in a sensitive state, load failures are a preferable defence compared to continuing with uncertainty.

When in a crashed state, the integration will delay repeatedly hitting the Solcast API.

Stored format on disk:

    {
        "presumed_dead": bool,
        "sensitive": bool,
        "crash_time": str | None, (ISO format)
        "exception_code": str | None,
        "translation_key": str | None,
        "translation_placeholders": dict[str, Any] | None,
    }
"""

from dataclasses import dataclass
from datetime import datetime as dt
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    IntegrationError,
)
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1

_CODE_TO_EXCEPTION: dict[str, type[IntegrationError]] = {
    "auth_failed": ConfigEntryAuthFailed,
    "not_ready": ConfigEntryNotReady,
    "fatal": ConfigEntryError,
}
_EXCEPTION_TO_CODE: dict[type[IntegrationError], str] = {cls: code for code, cls in _CODE_TO_EXCEPTION.items()}


class _StoredState(TypedDict, total=False):
    presumed_dead: bool
    sensitive: bool
    crash_time: str | None
    exception_code: str | None
    translation_key: str | None
    translation_placeholders: dict[str, Any] | None


@dataclass
class State:
    """In-memory view of state."""

    presumed_dead: bool = False
    sensitive: bool = False
    crash_time: dt | None = None
    exception_class: type[IntegrationError] | None = None
    translation_key: str | None = None
    translation_placeholders: dict[str, Any] | None = None


class GlobalStateStore(Store[_StoredState]):
    """Forced global backing store."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise with a simple all-entries key string."""
        super().__init__(hass, _STORAGE_VERSION, f"{DOMAIN}.state")


class StateStore:
    """State backed by helpers.storage.Store."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the backing store."""
        self._store = GlobalStateStore(hass)
        self.state: State = State()

    async def async_load(self) -> None:
        """Populate self.state from disk, if any data is present."""
        data = await self._store.async_load()
        if not data:
            return
        self.state.presumed_dead = bool(data.get("presumed_dead", False))
        crash_time = data.get("crash_time")
        self.state.crash_time = dt.fromisoformat(crash_time) if crash_time else None
        exception_code = data.get("exception_code")
        self.state.exception_class = _CODE_TO_EXCEPTION.get(exception_code) if exception_code else None
        self.state.translation_key = data.get("translation_key")
        self.state.translation_placeholders = data.get("translation_placeholders")
        self.state.sensitive = bool(data.get("sensitive", False))

    def _as_stored(self) -> _StoredState:
        crash_time = self.state.crash_time
        exception_class = self.state.exception_class
        return {
            "presumed_dead": self.state.presumed_dead,
            "sensitive": self.state.sensitive,
            "crash_time": crash_time.isoformat() if crash_time else None,
            "exception_code": _EXCEPTION_TO_CODE.get(exception_class) if exception_class else None,
            "translation_key": self.state.translation_key,
            "translation_placeholders": self.state.translation_placeholders,
        }

    async def async_save(self) -> None:
        """Persist the current self.state to disk."""
        await self._store.async_save(self._as_stored())

    async def async_clear(self) -> None:
        """Reset state and remove persisted data."""
        if not self.state.sensitive:
            self.state = State()
            await self._store.async_remove()
        else:
            self.state.presumed_dead = False
            self.state.crash_time = None
            self.state.translation_key = None
            self.state.translation_placeholders = None
            await self._store.async_save(self._as_stored())

    async def async_clear_after_success(self) -> None:
        """Clear saved state after a successful setup."""
        self.state.presumed_dead = False
        self.state.crash_time = None
        self.state.translation_key = None
        self.state.translation_placeholders = None
        self.state.sensitive = False
        await self._store.async_save(self._as_stored())

    @property
    def sensitive(self) -> bool:
        """Return whether the state is currently sensitive."""
        return self.state.sensitive


_STORE: dict[str, StateStore] = {}


async def async_get(hass: HomeAssistant, entry_id: str) -> StateStore:
    """Return the state store for the entry, loading from disk on first use."""
    store = _STORE.get(entry_id)  # Keyed by entry_id to enable global variable use safely.
    if store is None:
        store = StateStore(hass, entry_id)
        await store.async_load()
        _STORE[entry_id] = store
    return store


async def raise_and_record(
    hass: HomeAssistant,
    entry: ConfigEntry | None,
    exception: type[IntegrationError],
    translation_key: str,
    translation_placeholders: dict | None = None,
) -> None:
    """Record the exception details on the state store and raise.

    When entry is None (only possible in tests) the crash is still raised but no state is persisted.
    """
    if entry is not None:
        store = await async_get(hass, entry.entry_id)
        store.state.exception_class = exception
        store.state.translation_key = translation_key
        store.state.translation_placeholders = translation_placeholders
        await store.async_save()
    raise exception(translation_domain=DOMAIN, translation_key=translation_key, translation_placeholders=translation_placeholders)


async def set_sensitive(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set the state to sensitive, so the integration can respond to repeated failures with controlled behavior."""
    store = await async_get(hass, entry.entry_id)
    store.state.sensitive = True
    await store.async_save()
