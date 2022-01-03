"""The Barry App integration."""
import logging
from random import randint
from datetime import datetime, timedelta
from pytz import timezone

from pybarry import Barry

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config,HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_change

from .const import DOMAIN, PRICE_CODE
from .events import async_track_time_change_in_tz

PLATFORMS = ["sensor"]
EVENT_NEW_DATA = "barry_update"
RANDOM_MINUTE = randint(0, 10)
RANDOM_SECOND = randint(0, 59)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

class BarryData:
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self.listeners = []
        self.barry_connection = None

async def _dry_setup(hass, entry) -> bool:
    """Setup"""
    _LOGGER.debug("Running _dry_setup")

    if DOMAIN not in hass.data:
        _LOGGER.debug("Setting up integration: %s", entry)
        api = BarryData(hass)

        api.barry_connection = Barry(
            access_token=entry.data[CONF_ACCESS_TOKEN],
        )

        hass.data[DOMAIN] = api

        async def new_hr(n):
            """Callback to tell the sensors to update on a new hour."""
            _LOGGER.debug("Called new_hr callback")
            async_dispatcher_send(hass, EVENT_NEW_DATA)

        async def new_data_cb(n):
            """Callback to fetch new data for tomorrows prices at 1300ish CET
            and notify any sensors, about the new data
            """
            _LOGGER.debug("Called new_data_cb")
            async_dispatcher_send(hass, EVENT_NEW_DATA)

        cb_update_tomorrow = async_track_time_change_in_tz(
            hass,
            new_data_cb,
            hour=13,
            minute=RANDOM_MINUTE,
            second=RANDOM_SECOND,
            tz=timezone("Europe/Stockholm"),
        )

        cb_new_hr = async_track_time_change(
            hass, new_hr, minute=0, second=0
        )

        api.listeners.append(cb_update_tomorrow)
        api.listeners.append(cb_new_hr)

    return True


async def async_setup(hass: HomeAssistant, config: ConfigEntry):
#     """Set up the Barry component."""
#     #hass.data[DOMAIN] = {}
#     #return await _dry_setup(hass, entry.data)
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Set up a config entry."""
    res = await _dry_setup(hass, entry)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return res


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        for unsub in hass.data[DOMAIN].listeners:
            unsub()
        hass.data.pop(DOMAIN)

        return True

    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
