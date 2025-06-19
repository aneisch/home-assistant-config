""" Le Config Flow """

import logging
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigFlow,
    FlowResult,
    OptionsFlow,
    ConfigEntry,
)
from homeassistant.data_entry_flow import FlowHandler

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .config_schema import (
    types_schema_devices,
    central_config_schema,
    managed_device_schema,
    power_managed_device_schema,
)

from .coordinator import SolarOptimizerCoordinator

_LOGGER = logging.getLogger(__name__)


class SolarOptimizerBaseConfigFlow(FlowHandler):
    """La classe qui implémente le config flow pour notre DOMAIN.
    Elle doit dériver de FlowHandler"""

    # La version de notre configFlow. Va permettre de migrer les entités
    # vers une version plus récente en cas de changement
    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self, infos) -> None:
        super().__init__()
        _LOGGER.debug("CTOR BaseConfigFlow infos: %s", infos)
        self._infos: dict = infos

        # Coordinator should be initialized
        self._coordinator = SolarOptimizerCoordinator.get_coordinator()
        if not self._coordinator:
            _LOGGER.warning("Coordinator is not initialized yet. First run ?")

        self._user_inputs: dict = {}
        self._placeholders: dict = {}

    async def generic_step(self, step_id, data_schema, user_input, next_step_function):
        """A generic method step"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_%s user_input=%s", step_id, user_input
        )

        defaults = self._infos.copy()
        errors = {}

        if user_input is not None:
            defaults.update(user_input or {})
            try:
                await self.validate_input(user_input, step_id)
            except UnknownEntity as err:
                errors[str(err)] = "unknown_entity"
            except InvalidTime as err:
                errors[str(err)] = "format_time_invalid"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.merge_user_input(data_schema, user_input)
                # Add default values for central config flags
                _LOGGER.debug("_info is now: %s", self._infos)
                return await next_step_function()

        # ds = schema_defaults(data_schema, **defaults)  # pylint: disable=invalid-name
        ds = self.add_suggested_values_to_schema(
            data_schema=data_schema, suggested_values=defaults
        )  # pylint: disable=invalid-name

        return self.async_show_form(
            step_id=step_id,
            data_schema=ds,
            errors=errors,
            description_placeholders=self._placeholders,
        )

    def merge_user_input(self, data_schema: vol.Schema, user_input: dict):
        """For each schema entry not in user_input, set or remove values in infos"""
        self._infos.update(user_input)
        for key, _ in data_schema.schema.items():
            if key not in user_input and isinstance(key, vol.Marker):
                _LOGGER.debug(
                    "add_empty_values_to_user_input: %s is not in user_input", key
                )
                if key in self._infos:
                    self._infos.pop(key)
            # else:  This don't work but I don't know why. _infos seems broken after this (Not serializable exactly)
            #     self._infos[key] = user_input[key]

        _LOGGER.debug("merge_user_input: infos is now %s", self._infos)

    async def validate_input(
        self, data: dict, step_id  # pylint: disable=unused-argument
    ) -> None:
        """Validate the user input."""

        # check the entity_ids
        for conf in [
            CONF_POWER_CONSUMPTION_ENTITY_ID,
            CONF_POWER_PRODUCTION_ENTITY_ID,
            CONF_SELL_COST_ENTITY_ID,
            CONF_BUY_COST_ENTITY_ID,
            CONF_SELL_TAX_PERCENT_ENTITY_ID,
        ]:
            d = data.get(conf, None)  # pylint: disable=invalid-name
            if not isinstance(d, list):
                d = [d]
            for e in d:
                if e is not None and self.hass.states.get(e) is None:
                    _LOGGER.error(
                        "Entity id %s doesn't have any state. We cannot use it in the Versatile Thermostat configuration",  # pylint: disable=line-too-long
                        e,
                    )
                    raise UnknownEntity(conf)

        for conf in [CONF_RAZ_TIME, CONF_OFFPEAK_TIME]:
            try:
                d = data.get(conf, None)
                if d is not None:
                    validate_time_format(d)
            except vol.Invalid as err:
                raise InvalidTime(conf)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps user"""
        _LOGGER.debug("Into ConfigFlow.async_step_user user_input=%s", user_input)

        if not self._coordinator or not self._coordinator.is_central_config_done:
            return await self.async_step_device_central(user_input)

        schema = types_schema_devices
        next_step = None
        if user_input is not None:
            if user_input.get(CONF_DEVICE_TYPE) == CONF_DEVICE:
                next_step = self.async_step_device
            elif user_input.get(CONF_DEVICE_TYPE) == CONF_POWERED_DEVICE:
                next_step = self.async_step_powered_device
            else:
                raise ConfigurationError("Unknown device type")

        return await self.generic_step("user", schema, user_input, next_step)

    async def async_step_device_central(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the flow steps for central device"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_device_central user_input=%s", user_input
        )

        if user_input is not None:
            # Check if the entity_ids are valid
            user_input[CONF_NAME] = "Configuration"
            user_input[CONF_DEVICE_TYPE] = CONF_DEVICE_CENTRAL
            # await self.validate_input(user_input, "device_central")

        return await self.generic_step(
            "device_central",
            central_config_schema,
            user_input,
            self.async_step_finalize,
        )

    async def async_step_device(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps for device"""
        _LOGGER.debug("Into ConfigFlow.async_step_device user_input=%s", user_input)

        return await self.generic_step(
            "device", managed_device_schema, user_input, self.async_step_finalize
        )

    async def async_step_powered_device(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the flow steps for powered device"""
        _LOGGER.debug(
            "Into ConfigFlow.async_step_powered_device user_input=%s", user_input
        )

        if user_input is not None:
            # Check if the entity_ids are valid
            await self.validate_input(user_input, "powered_device")

        return await self.generic_step(
            "powered_device",
            power_managed_device_schema,
            user_input,
            self.async_step_finalize,
        )

    def is_matching(self, entry: ConfigEntry) -> bool:
        """Check if the entry matches the current flow."""
        return entry.data.get("domain") == SOLAR_OPTIMIZER_DOMAIN

    async def async_step_finalize(self, user_input: dict | None = None) -> FlowResult:
        """Handle the flow steps for finalization"""
        _LOGGER.debug("Into ConfigFlow.async_step_finalize user_input=%s", user_input)

        if user_input is not None:
            # Check if the entity_ids are valid
            await self.validate_input(user_input, "finalize")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get options flow for this handler"""
        return SolarOptimizerOptionsFlow(config_entry)

class SolarOptimizerConfigFlow(
    SolarOptimizerBaseConfigFlow, ConfigFlow, domain=SOLAR_OPTIMIZER_DOMAIN
):
    """The real config flow for Solar Optimizer"""

    def __init__(self) -> None:
        # self._info = dict()
        super().__init__(dict())
        _LOGGER.debug("CTOR ConfigFlow")

    async def async_step_finalize(self, user_input: dict | None = None) -> FlowResult:
        """Finalization of the ConfigEntry creation"""
        _LOGGER.debug("ConfigFlow.async_finalize")
        await super().async_step_finalize(user_input)

        return self.async_create_entry(title=self._infos[CONF_NAME], data=self._infos)


class SolarOptimizerOptionsFlow(SolarOptimizerBaseConfigFlow, OptionsFlow):
    """The class which enable to modified the configuration"""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialisation de l'option flow. On a le ConfigEntry existant en entrée"""
        super().__init__(config_entry.data.copy())
        _LOGGER.debug(
            "CTOR SolarOptimizerOptionsFlow info: %s, entry_id: %s",
            self._infos,
            config_entry.entry_id,
        )

    async def async_step_init(self, user_input=None):
        """Manage options."""
        _LOGGER.debug(
            "Into OptionsFlowHandler.async_step_init user_input =%s",
            user_input,
        )

        if self._infos.get(CONF_DEVICE_TYPE) == CONF_DEVICE_CENTRAL:
            return await self.async_step_device_central(user_input)
        elif self._infos.get(CONF_DEVICE_TYPE) == CONF_DEVICE:
            return await self.async_step_device(user_input)
        elif self._infos.get(CONF_DEVICE_TYPE) == CONF_POWERED_DEVICE:
            return await self.async_step_powered_device(user_input)

    async def async_step_finalize(self, user_input: dict | None = None) -> FlowResult:
        _LOGGER.info(
            "Recreating entry %s due to configuration change. New config is now: %s",
            self.config_entry.entry_id,
            self._infos,
        )
        await super().async_step_finalize(user_input)

        self.hass.config_entries.async_update_entry(self.config_entry, data=self._infos)
        return self.async_create_entry(title=None, data=None)

    # async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
    #     """Gestion de l'étape 'user'. Point d'entrée de notre
    #     configFlow. Cette méthode est appelée 2 fois :
    #     1. une première fois sans user_input -> on affiche le formulaire de configuration
    #     2. une deuxième fois avec les données saisies par l'utilisateur dans user_input -> on sauvegarde les données saisies
    #     """
    #     user_form = vol.Schema(central_config_schema)


#
#     if user_input is None:
#         _LOGGER.debug(
#             "config_flow step user (1). 1er appel : pas de user_input -> on affiche le form user_form"
#         )
#         return self.async_show_form(
#             step_id="init",
#             data_schema=add_suggested_values_to_schema(
#                 data_schema=user_form,
#                 suggested_values=self._user_inputs,
#             ),
#         )
#
#     # 2ème appel : il y a des user_input -> on stocke le résultat
#     self._user_inputs.update(user_input)
#     _LOGGER.debug(
#         "config_flow step_user (2). L'ensemble de la configuration est: %s",
#         self._user_inputs,
#     )
#
#     # On appelle le step de fin pour enregistrer les modifications
#     return await self.async_end()

# async def async_end(self):
#     """Finalization of the ConfigEntry creation"""
#     _LOGGER.info(
#         "Recreation de l'entry %s. La nouvelle config est maintenant : %s",
#         self.config_entry.entry_id,
#         self._user_inputs,
#     )
#
#     # Modification des data de la configEntry
#     # (et non pas ajout d'un objet options dans la configEntry)
#     self.hass.config_entries.async_update_entry(
#         self.config_entry, data=self._user_inputs
#     )
#     # Suppression de l'objet options dans la configEntry
#     return self.async_create_entry(title=None, data=None)
