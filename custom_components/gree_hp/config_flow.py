"""Config flow for Gree Heat Pump integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gree Heat Pump."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        return self.async_create_entry(
            title=f"Gree Heat Pump ({user_input[CONF_HOST]})",
            data=user_input,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Gree Heat Pump."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            # Validate polling interval is between 1 and 10, default to 10 if invalid
            polling_interval = user_input.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
            if not isinstance(polling_interval, int) or polling_interval < 1 or polling_interval > 10:
                polling_interval = DEFAULT_POLLING_INTERVAL

            return self.async_create_entry(
                title="",
                data={CONF_POLLING_INTERVAL: polling_interval}
            )

        current_polling_interval = self.config_entry.options.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_POLLING_INTERVAL,
                    default=current_polling_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=10))
            })
        )
