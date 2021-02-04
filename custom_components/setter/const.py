import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_ENTITY_ID

import voluptuous as vol

DOMAIN = "setter"

SERVICE_DELETE = "delete"
SERVICE_DELETE_SCHEMA = vol.Schema({vol.Required(CONF_ENTITY_ID): cv.entity_id})

SERVICE_SET = "set"
SERVICE_SET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required("state"): str,
        vol.Required("attributes"): dict,
    }
)
