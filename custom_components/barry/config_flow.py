"""Adds config flow for Barry integration."""
# pylint: disable=attribute-defined-outside-init
import asyncio
import logging

from .pybarry import Barry, InvalidToken
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback

from .const import DOMAIN, PRICE_CODE, MPID

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class BarryConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Barry integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Barry options callback."""
        return BarryOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        data_schema = vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN].strip()

            barry_connection = Barry(
                access_token=access_token,
            )

            errors = {}
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, barry_connection.get_all_metering_points, True
                )
            except InvalidToken:
                errors[CONF_ACCESS_TOKEN] = "invalid_access_token"
            except Exception:  # pylint: disable=broad-except
                errors[CONF_ACCESS_TOKEN] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=data_schema,
                    errors=errors,
                )
            self.init_info = barry_connection
            self.access_token = access_token
            return await self.async_step_metering_point()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    async def async_step_metering_point(self, user_input=None):
        """Handle the metering point selection step."""
        mpids = await self.hass.async_add_executor_job(self.init_info.get_all_metering_points)

        _LOGGER.debug("Got mpids %s", mpids)
        mpids_display = [mpid["address"] for mpid in mpids]
        data_schema = vol.Schema(
            {vol.Required("metering_point"): vol.In(mpids_display)}
        )
        if user_input:
            _LOGGER.debug("Got user input: %s", user_input)
            selected_meter = next(
                (item for item in mpids if item["address"] == user_input["metering_point"]), None)

            if selected_meter is None:
                return self.async_abort(reason="missing_meter")

            _LOGGER.debug("Selected meter: %s", selected_meter["mpid"])

            price_code = selected_meter["priceCode"]
            _LOGGER.debug("Price code: %s", price_code)
            mpid = selected_meter["mpid"]
            _LOGGER.debug("MPID: %s", mpid)

            unique_id = "barry_" + str(mpid)
            _LOGGER.debug("Created unique ID: %s", unique_id)
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Barry - " + selected_meter["mpid"],
                data={
                    CONF_ACCESS_TOKEN: self.access_token,
                    PRICE_CODE: price_code,
                    MPID: mpid
                },
            )

        return self.async_show_form(
            step_id="metering_point",
            data_schema=data_schema,
        )


class BarryOptionsFlowHandler(config_entries.OptionsFlow):
    """Option Flow for Barry component"""

    def __init__(self, config_entry):
        self._access_token = config_entry.data[CONF_ACCESS_TOKEN] if CONF_ACCESS_TOKEN in config_entry.data else None
        self._price_code = config_entry.data[PRICE_CODE] if PRICE_CODE in config_entry.data else None
        self._mpid = config_entry.data[MPID] if MPID in config_entry.data else None
        self._errors = {}

    async def async_step_init(self, usser_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._access_token = user_input[CONF_ACCESS_TOKEN].strip()

        data_schema = {
            vol.Required(CONF_ACCESS_TOKEN, default=self._access_token): str,
        }

        if user_input is not None:
            return self.async_create_entry(
                title="Barry - " + self._mpid,
                data={
                    CONF_ACCESS_TOKEN: self._access_token,
                    PRICE_CODE: self._price_code,
                    MPID: self._mpid
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=self._errors,
        )
