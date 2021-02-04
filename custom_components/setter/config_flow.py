from homeassistant import config_entries

from .const import DOMAIN


class SetterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Setter", data=user_input)
        return self.async_show_form(step_id="user")

    async_step_import = async_step_user
