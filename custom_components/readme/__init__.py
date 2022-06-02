"""
Use Jinja and data from Home Assistant to generate your README.md file

For more details about this component, please refer to
https://github.com/custom-components/readme
"""
from __future__ import annotations

import asyncio
import json
import os
from shutil import copyfile
from typing import Any, Dict, List

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.template import AllStates
from homeassistant.loader import Integration, IntegrationNotFound, async_get_integration
from homeassistant.setup import async_get_loaded_integrations
from jinja2 import Template


from .const import DOMAIN, DOMAIN_DATA, LOGGER, STARTUP_MESSAGE

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Optional("convert_lovelace"): cv.boolean})},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up this component using YAML."""
    if config.get(DOMAIN) is None:
        # We get her if the integration is set up using config flow
        return True

    # Print startup message
    LOGGER.info(STARTUP_MESSAGE)

    # Create DATA dict
    hass.data.setdefault(DOMAIN_DATA, config[DOMAIN])

    await add_services(hass)

    def _create_initial_files():
        create_initial_files(hass)

    await hass.async_add_executor_job(_create_initial_files)

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry):
    """Set up this integration using UI."""
    if config_entry.source == config_entries.SOURCE_IMPORT:
        if hass.data.get(DOMAIN_DATA) is None:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
        return True

    # Print startup message
    LOGGER.info(STARTUP_MESSAGE)

    # Create DATA dict
    hass.data[DOMAIN_DATA] = config_entry.data

    await add_services(hass)

    def _create_initial_files():
        create_initial_files(hass)

    await hass.async_add_executor_job(_create_initial_files)

    return True


def create_initial_files(hass: HomeAssistant):
    """Create the initial files for this integration."""
    if not os.path.exists(hass.config.path("templates")):
        os.mkdir(hass.config.path("templates"))

    if not os.path.exists(hass.config.path("templates/README.j2")):

        copyfile(
            hass.config.path("custom_components/readme/default.j2"),
            hass.config.path("templates/README.j2"),
        )


async def convert_lovelace(hass: HomeAssistant):
    """Convert the lovelace configuration."""
    if os.path.exists(hass.config.path(".storage/lovelace")):
        content = (
            json.loads(await read_file(hass, ".storage/lovelace") or {})
            .get("data", {})
            .get("config", {})
        )

        await write_file(hass, "ui-lovelace.yaml", content, as_yaml=True)


async def async_remove_entry(hass: HomeAssistant, config_entry):
    """Handle removal of an entry."""
    hass.services.async_remove(DOMAIN, "generate")
    hass.data.pop(DOMAIN_DATA)


async def read_file(hass: HomeAssistant, path: str) -> Any:
    """Read a file."""

    def read():
        with open(hass.config.path(path), "r") as open_file:
            return open_file.read()

    return await hass.async_add_executor_job(read)


async def write_file(
    hass: HomeAssistant, path: str, content: Any, as_yaml=False
) -> None:
    """Write a file."""

    def write():
        with open(hass.config.path(path), "w") as open_file:
            if as_yaml:
                yaml.dump(content, open_file, default_flow_style=False, allow_unicode=True)
            else:
                open_file.write(content)

    await hass.async_add_executor_job(write)


async def add_services(hass: HomeAssistant):
    """Add services."""
    # Service registration

    async def service_generate(_call):
        """Generate the files."""
        if hass.data[DOMAIN_DATA].get("convert") or hass.data[DOMAIN_DATA].get(
            "convert_lovelace"
        ):
            await convert_lovelace(hass)

        custom_components = await get_custom_integrations(hass)
        hacs_components = get_hacs_components(hass)
        installed_addons = get_ha_installed_addons(hass)

        variables = {
            "custom_components": custom_components,
            "states": AllStates(hass),
            "hacs_components": hacs_components,
            "addons": installed_addons,
        }

        content = await read_file(hass, "templates/README.j2")

        template = Template(content)
        try:
            render = template.render(variables)
            await write_file(hass, "README.md", render)
        except Exception as exception:
            LOGGER.error(exception)

    hass.services.async_register(DOMAIN, "generate", service_generate)


def get_hacs_components(hass: HomeAssistant):
    if (hacs := hass.data.get("hacs")) is None:
        return []

    return [
        {
            **repo.data.to_json(),
            "name": get_repository_name(repo),
            "documentation": f"https://github.com/{repo.data.full_name}",
        }
        for repo in hacs.repositories.list_downloaded or []
    ]


@callback
def get_ha_installed_addons(hass: HomeAssistant) -> List[Dict[str, Any]]:
    if not hass.components.hassio.is_hassio():
        return []
    supervisor_info = hass.components.hassio.get_supervisor_info()

    if supervisor_info:
        return supervisor_info.get("addons", [])
    return []


def get_repository_name(repository) -> str:
    """Return the name of the repository for use in the frontend."""
    name = None

    if repository.repository_manifest.name:
        name = repository.repository_manifest.name
    else:
        name = repository.data.full_name.split("/")[-1]

    name = name.replace("-", " ").replace("_", " ").strip()

    if name.isupper():
        return name

    return name.title()


async def get_custom_integrations(hass: HomeAssistant):
    """Return a list with custom integration info."""
    custom_integrations = []
    configured_integrations: List[
        Integration | IntegrationNotFound | BaseException
    ] = await asyncio.gather(
        *[
            async_get_integration(hass, domain)
            for domain in async_get_loaded_integrations(hass)
        ],
        return_exceptions=True,
    )

    for integration in configured_integrations:
        if isinstance(integration, IntegrationNotFound):
            continue

        if isinstance(integration, BaseException):
            raise integration

        if integration.disabled or integration.is_built_in:
            continue

        custom_integrations.append(
            {
                "domain": integration.domain,
                "name": integration.name,
                "documentation": integration.documentation,
                "version": integration.version,
                "codeowners": integration.manifest.get("codeowners"),
            }
        )

    return custom_integrations
