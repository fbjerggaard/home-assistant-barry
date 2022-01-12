"""Platform for sensor integration."""
import logging
import math

from datetime import timedelta
from operator import itemgetter
from statistics import mean

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_utils

import dateutil.parser

from .const import DOMAIN, PRICE_CODE, MPID

from . import EVENT_NEW_DATA

_LOGGER = logging.getLogger(__name__)


def _dry_setup(hass, config, add_devices, discovery_info=None):
    """Setup platform"""
    _LOGGER.debug("Dumping config %r", config)
    _LOGGER.debug("Dumping hass data", hass.data)
    barry_connection = hass.data[DOMAIN].barry_connection
    price_code = config[PRICE_CODE]
    meter_id = config[MPID]
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
        self._raw_today = None
        self._raw_tomorrow = None
        self._today = None
        self._tomorrow = None
        self._average = None
        self._max = None
        self._min = None
        self._off_peak_1 = None
        self._off_peak_2 = None
        self._peak = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": DOMAIN,
        }

    @property
    def name(self) -> str:
        return self.unique_id

    @property
    def unique_id(self):
        name = "barry_%s_%s_%s" % (
            self._price_type,
            self._price_code,
            self._meter_id,
        )
        name = name.lower().replace(".", "").replace(" ", "_")
        return name

    @property
    def state(self) -> float:
        return self.current_total_price

    @property
    def unit(self) -> str:
        return self._price_type

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
            "raw_today": self._raw_today,
            "raw_tomorrow": self._raw_tomorrow,
            "today": self._today,
            "tomorrow": self._tomorrow,
            "average": self._average,
            "off_peak_1": self._off_peak_1,
            "off_peak_2": self._off_peak_2,
            "peak": self._peak,
            "min": self._min,
            "max": self._max,
        }

    @property
    def current_total_price(self) -> float:
        return self._current_total_price

    @property
    def current_spot_price(self) -> float:
        return self._current_spot_price

    @property
    def raw_today(self) -> list:
        return self._raw_today

    @property
    def raw_tomorrow(self) -> list:
        return self._raw_tomorrow

    @property
    def today(self) -> list:
        return self._today

    @property
    def today(self) -> list:
        return self._tomorrow

    @property
    def device_class(self) -> str:
        return "monetary"

    def _update_current_price(self) -> None:
        _LOGGER.debug("Updating current price")
        _LOGGER.debug("barry_home: %s", self._barry_home)
        total_price = self._barry_home.get_current_total_price(self._meter_id)
        spot_price = self._barry_home.get_current_spot_price(self._price_code)
        _LOGGER.debug("Got prices: %s | %s", total_price, spot_price)
        self._current_total_price = total_price["value"]
        self._current_spot_price = spot_price["value"]
        _LOGGER.debug("Updated %s with new prices: %s/%s", self.name,
                      self._current_total_price, self._current_spot_price)

    def _update_prices(self) -> None:
        _LOGGER.debug("Updating all prices")
        data_today = self._barry_home.get_total_prices_today(self._meter_id)
        data_tomorrow = self._barry_home.get_total_prices_tomorrow(
            self._meter_id)
        self._raw_today, self._today = self._map_prices(data_today)
        self._raw_tomorrow, self._tomorrow = self._map_prices(data_tomorrow)

        _LOGGER.debug("Fixed data today: %s", self._raw_today)
        _LOGGER.debug("Fixed data tomorrow: %s", self._raw_tomorrow)
        _LOGGER.debug("Raw prices today: %s", self._today)
        _LOGGER.debug("Raw prices tomorrow: %s", self._tomorrow)

        offpeak1 = self._today[0:8]
        peak = self._today[9:17]
        offpeak2 = self._today[20:]

        self._peak = mean(peak)
        self._off_peak_1 = mean(offpeak1)
        self._off_peak_2 = mean(offpeak2)
        self._average = mean(self._today)
        self._min = min(self._today)
        self._max = max(self._today)

    def _map_prices(self, data) -> dict:
        newdata = []
        rawprices = []
        # Sorting to ensure we have the correct order
        data.sort(key=itemgetter('start'))
        for entry in data:
            newdata.append({
                "start": dt_utils.as_local(dateutil.parser.isoparse(entry["start"])),
                "end": dt_utils.as_local(dateutil.parser.isoparse(entry["end"])),
                "value": entry["value"]
            })
            rawprices.append(entry["value"])

        return newdata, rawprices

    async def check_stuff(self) -> None:
        _LOGGER.debug("Called check_stuff")
        await self.hass.async_add_executor_job(self._update_current_price)
        await self.hass.async_add_executor_job(self._update_prices)

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        await super().async_added_to_hass()
        _LOGGER.debug("called async_added_to_hass %s", self.name)
        async_dispatcher_connect(self.hass, EVENT_NEW_DATA, self.check_stuff)

        await self.check_stuff()
