from dataclasses import asdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.storage import Store

from .connector.xiaomi_cloud.connector import XiaomiCloudConnectorConfig
from .const import STORAGE_VERSION, DOMAIN


async def save_connector_config(hass: HomeAssistant, mac: str, config: XiaomiCloudConnectorConfig) -> None:
    store = _create_store(hass, mac)
    connector_config = asdict(config)
    await store.async_save({"connector_config": connector_config})


async def restore_connector_config(hass: HomeAssistant, mac: str) -> XiaomiCloudConnectorConfig | None:
    store = _create_store(hass, mac)
    stored_data = await store.async_load()
    if stored_data is None:
        return None
    connector_config = stored_data.get("connector_config", None)
    if connector_config is None:
        return None
    return XiaomiCloudConnectorConfig.from_dict(connector_config)


def _create_store(hass: HomeAssistant, mac: str) -> Store:
    store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{format_mac(mac)}")
    return store
