"""Config flow for HKV integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry, OptionsFlow

from .const import DOMAIN
from .hub import HKVHub
from homeassistant.components.hkv.const import CONF_DEV, CONF_BAUD,\
    CONF_INTERVAL, SCAN_REGISTERS

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEV,default='/dev/ttyUSB0'): str,
        vol.Required(CONF_BAUD,default=115200): int,
        vol.Required(CONF_INTERVAL, default=30): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = HKVHub(data[CONF_DEV], data[CONF_BAUD])
    try:
        hub.connect()
        _LOGGER.debug("connection was succesfull")
        discovered_devices = await hub.scan_connected_devices() 
        _LOGGER.debug("successfully discovered devices")  
    except:
        _LOGGER.error("failed to connect to the HKV device") 
        raise CannotConnect()

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "HKV",
            "data": discovered_devices}


class HKVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HKV."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry,) -> HKVOptionFlowHandler:
        """Get the options flow for this handler."""
        return HKVOptionFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}
        already_configured = False

        if user_input[CONF_INTERVAL] < 10:
            user_input[CONF_INTERVAL] = 10

        try:
            #not yet working
            await self.async_set_unique_id("hkv")
            self._abort_if_unique_id_configured()
        except Exception as e:
            errors["base"] = "already_configured"
            already_configured = True

        if not already_configured:

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                options = user_input
                return self.async_create_entry(title=info["title"], data={ SCAN_REGISTERS: info["data"] }, options=options, )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)
    

class HKVOptionFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    logger = logging.getLogger(__name__)

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.area = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_DEV,default=self.config_entry.options.get(CONF_DEV),): str,
                vol.Required(CONF_BAUD,default=self.config_entry.options.get(CONF_BAUD),): int,
                vol.Required(CONF_INTERVAL,default=self.config_entry.options.get(CONF_INTERVAL),): int,
                }
            ),
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
    
