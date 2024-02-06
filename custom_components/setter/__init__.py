import logging

from homeassistant.core import Context
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_component import EntityComponent

from .const import *

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    if DOMAIN not in config:
        return True
    return setup_entry(hass, config)


async def async_setup_entry(hass, config_entry):
    result = await hass.async_add_executor_job(setup_entry, hass, config_entry)
    return result


def setup_entry(hass, config_entry):
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    saver_entity = SaverEntity()
    component.add_entities([saver_entity])

    def delete(call):
        data = call.data
        entity_id = data[CONF_ENTITY_ID]
        hass.states.set(entity_id, "unavailable", {})
        saver_entity.delete(entity_id)

    def do_set(call):
        data = call.data
        entity_id = data[CONF_ENTITY_ID]
        state = data["state"]
        attributes = data["attributes"]
        hass.states.set(entity_id, state, attributes)
        saver_entity.save(entity_id)

    hass.services.register(DOMAIN, SERVICE_DELETE, delete, SERVICE_DELETE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_SET, do_set, SERVICE_SET_SCHEMA)

    for entity_id, data in saver_entity.get_all_entities().items():
        state = data["state"]
        attributes = data["attributes"]
        hass.states.set(entity_id, state, attributes)

    return True


class SaverEntity(RestoreEntity):
    def __init__(self):
        self._entities_db = {}

    def get_all_entities(self):
        return self._entities_db

    @property
    def name(self):
        return DOMAIN

    def delete(self, entity_id):
        self._entities_db.pop(entity_id)
        self.schedule_update_ha_state()

    def save(self, entity_id):
        self._entities_db[entity_id] = self.hass.states.get(entity_id)
        self.schedule_update_ha_state()

    @property
    def state_attributes(self):
        return {"entities": self._entities_db}

    @property
    def state(self):
        return len(self._entities_db)


    async def async_added_to_hass(self):
        state = await self.async_get_last_state()
        if state is not None \
                and state.attributes is not None \
                and "variables" in state.attributes and not isinstance(state.attributes["entities"], list) \
                and "entities" in state.attributes and not isinstance(state.attributes["variables"], list):
            self._variables_db = state.attributes["variables"]
            self._entities_db = state.attributes["entities"]
