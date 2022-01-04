import logging
import pytz
import requests

from datetime import datetime, timedelta

DEMO_TOKEN = ''
DEFAULT_TIMEOUT = 15

_LOGGER = logging.getLogger(__name__)


class InvalidToken(BaseException):
    pass


class Barry:

    def __init__(
            self,
            access_token=DEMO_TOKEN,
            timeout=DEFAULT_TIMEOUT,
    ):
        self.timeout = timeout
        self.headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json',
        }
        self.endpoint = "https://jsonrpc.barry.energy/json-rpc"

    @staticmethod
    def hour_rounder(t):
        # Rounds to nearest hour by adding a timedelta hour if minute >= 30
        return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
                + timedelta(hours=t.minute // 30))

    @staticmethod
    def get_currency(data):
        if data.get('country') == 'DK' or data.get('currency') == 'DKK':
            currency = 'kr./KWH'
        else:
            currency = '€/KWH'
        return currency

    def get_current_co2_emission(self, price_code):
        current_time = self.hour_rounder(
            datetime.utcnow().replace(microsecond=0)).isoformat() + 'Z'
        last_hour_date_time = self.hour_rounder(
            (datetime.utcnow() - timedelta(hours=1)).replace(microsecond=0)).isoformat() + 'Z'

        price_code = price_code.split('_')[-1]
        data = '{ "jsonrpc": "2.0", "id": 0, "method": "co.getbarry.api.v1.OpenApiController.getHourlyCo2Intensity", "params": [ "%s", "%s", "%s" ] }' % (
            price_code, last_hour_date_time, current_time)
        response = requests.post(
            self.endpoint, headers=self.headers, data=data)
        json_res = response.json()
        result = json_res.get('result')
        if result:
            result = result[0]
            value = result['carbonIntensity']
            return value, 'gCO2/kWh'
        else:
            return 'NA', '-'

    def get_current_spot_price(self, price_code):
        current_time = self.hour_rounder(
            datetime.utcnow().replace(microsecond=0)).isoformat() + 'Z'
        last_hour_date_time = self.hour_rounder(
            (datetime.utcnow() - timedelta(hours=1)).replace(microsecond=0)).isoformat() + 'Z'

        data = '{ "jsonrpc": "2.0", "id": 0, "method": "co.getbarry.api.v1.OpenApiController.getPrice", "params": [ "%s", "%s", "%s" ] }' % (
            price_code, last_hour_date_time, current_time)
        response = requests.post(
            self.endpoint, headers=self.headers, data=data)
        json_res = response.json()
        result = json_res.get('result')
        if result:
            result = result[0]
            value, currency = result['value'], self.get_currency(result)
            return {
                "value": value,
                "currency": currency
            }

    def get_current_total_price(self, mpid):
        current_time = self.hour_rounder(
            datetime.utcnow().replace(microsecond=0)).isoformat() + 'Z'
        last_hour_date_time = self.hour_rounder(
            (datetime.utcnow() - timedelta(hours=1)).replace(microsecond=0)).isoformat() + 'Z'

        data = '{ "jsonrpc": "2.0", "id": 0, "method": "co.getbarry.api.v1.OpenApiController.getTotalKwHPrice", "params": [ "%s", "%s", "%s" ] }' % (
            mpid, last_hour_date_time, current_time)
        response = requests.post(
            self.endpoint, headers=self.headers, data=data)
        json_res = response.json()
        result = json_res.get('result')
        if result:
            value, currency = result['value'], self.get_currency(result)
            return {
                "value": value,
                "currency": currency
            }

    def get_total_prices_offset(self, mpid, offset: int):
        dateNowMidnight = datetime.today().replace(
            second=0, microsecond=0, minute=0, hour=0)
        dtStart = str((dateNowMidnight + timedelta(days=offset)).astimezone(pytz.utc).date()
                      ) + "T" + str(dateNowMidnight.astimezone(pytz.utc).time()) + "Z"
        dtEnd = str((dateNowMidnight + timedelta(days=offset+1)).astimezone(pytz.utc).date()
                    ) + "T" + str(dateNowMidnight.astimezone(pytz.utc).time()) + "Z"

        data = '{ "jsonrpc": "2.0", "id": 0, "method": "co.getbarry.api.v1.OpenApiController.getTotalKwHourlyPrice", "params": [ "%s", "%s", "%s" ] }' % (
            mpid, dtStart, dtEnd)
        response = requests.post(
            self.endpoint, headers=self.headers, data=data)
        json_res = response.json()
        result = json_res.get('result')
        if result:
            return result
        else:
            raise Exception('No data returned')

    def get_total_prices_today(self, mpid):
        return self.get_total_prices_offset(mpid, 0)

    def get_total_prices_tomorrow(self, mpid):
        return self.get_total_prices_offset(mpid, 1)

    def get_all_metering_points(self, check_token=False):
        data = '{ "jsonrpc": "2.0", "id": 0, "method": "co.getbarry.api.v1.OpenApiController.getMeteringPoints", "params": [] }'
        response = requests.post(
            self.endpoint, headers=self.headers, data=data)
        json_res = response.json()
        if json_res.get('result'):
            if check_token:
                return True
            result = json_res['result']
            res = []
            for data in result:
                res.append({
                    "address": data['address']['formattedAddress'],
                    "mpid": data["mpid"],
                    "priceCode": data["priceCode"]
                })

            return res
        else:
            raise InvalidToken('Invalid access token')
