"""Platform for sensor integration."""
from datetime import timedelta
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, PRICE_CODE, MPID

from . import EVENT_NEW_DATA

_LOGGER = logging.getLogger(__name__)

def _dry_setup(hass, config, add_devices, discovery_info=None):
    """Setup platform"""
    _LOGGER.debug("Dumping config %r", config)
    barry_connection = hass.data[DOMAIN]
    price_code = hass.data[PRICE_CODE]
    meter_id = hass.data[MPID]
    sensor = BarrySensor(
        barry_connection, 
        price_code,
        meter_id
    )

    add_devices([sensor])

async def async_setup_platform(hass, config, add_devices, discovery_info=None) -> None:
    _LOGGER.debug("Setting up platform")
    _dry_setup(hass, config, add_devices)
    return True

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Barry sensor."""
    _LOGGER.debug("Setting up sensor")
    config = config_entry.data
    _dry_setup(hass, config, async_add_devices)
    return True

class BarrySensor(Entity):
    """Representation of a Sensor."""

    def __init__(
        self,
        barry_home,
        price_code,
        meter_id
    ) -> None:
        """Initialize the sensor."""
        self._barry_home = barry_home
        self._price_code = price_code
        self._meter_id = meter_id
        self._attr_name = "Electricity price Barry"
        self._current_total_price = None
        self._current_spot_price = None
        self._currency = "DKK"
        self._price_type = "kWh"

    @property
    def state(self) -> float:
        return self.current_total_price

    @property
    def icon(self) -> str:
        return "mdi:flash"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement this sensor expresses itself in."""
        return "%s/%s" % (self._currency, self._price_type)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "current_total_price": self.current_total_price,
            "current_spot_price": self.current_spot_price,
            "currency": self._currency,
        }

    @property
    def current_total_price(self) -> float:
        return self._current_total_price

    @property
    def current_spot_price(self) -> float:
        return self._current_spot_price

    def _update_current_price(self) -> None:
        _LOGGER.debug("Updating current price")
        self._current_total_price = self._barry_home.update_total_price(self._meter_id)
        self._current_spot_price = self._barry_home.update_spot_price(self._price_code)
        _LOGGER.debug("Updated %s with new prices: %s/%s", self.name, self._current_total_price, self._current_spot_price)

    async def check_stuff(self) -> None:
        _LOGGER.debug("Called check_stuff")
        await self.hass.async_add_executor_job(self._update_current_price)

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        await super().async_added_to_hass()
        _LOGGER.debug("called async_added_to_hass %s", self.name)
        async_dispatcher_connect(self.hass, EVENT_NEW_DATA, self.check_stuff)

        await self.check_stuff()