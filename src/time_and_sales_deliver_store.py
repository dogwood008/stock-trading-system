# Original: 
# https://github.com/lindomar-oliveira/backtrader-binance/blob/c3ea500d453ec16f925450c299be097bf99970e2/backtrader_binance/binance_store.py
# Great Thanks to Lindomar Oliveira!
#
# MIT License
# 
# Copyright (c) 2021 Lindomar Oliveira
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import NewType

import time

from functools import wraps
from math import floor

from backtrader.dataseries import TimeFrame
from backtrader import Position
from requests.exceptions import ConnectTimeout, ConnectionError

# from .binance_broker import BinanceBroker
# from .binance_feed import BinanceData
import sys, os
from datetime import date, datetime
import urllib3
import json
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
from time_and_sales_deliver_broker import TimeAndSalesDeliverBroker, TimeAndSaledDeliverEnum
from time_and_sales_deliver_feed import TimeAndSalesDeliverData

RawHistData = NewType('HistData', list[list[str, str, str]])
HistData = NewType('HistData', list[list[datetime, float, float]]) # [datetime, price, volume]
Positions = NewType('Positions', list[datetime, Position])

class TimeAndSalesDeliverStore(object):
    def __init__(self, host: str, port: int=80, protocol='http', retries=5):
        self.host = host
        self.port = port
        self.protocol = protocol
        self.retries = retries
        self._broker = TimeAndSalesDeliverBroker(store=self)
        self._data: HistData = None
        self._http = urllib3.PoolManager()

    def getbroker(self):
        return self._broker

    def getdata(self, stock_code: str, \
            start_dt: datetime=None, end_dt: datetime=None) -> TimeAndSalesDeliverData:
        '''
        FIXME
        '''
        if not self._data:
            self._data = self.get_historical_data(stock_code, start_dt, end_dt)
        return self._data

    def get_historical_data(self, stock_code: str,
            from_dt: datetime, to_dt: datetime) -> TimeAndSalesDeliverData:
        '''
        http://lvh.me:4567/7974/2022-01-01T12:34:56 のようなフォーマットで取りに行く
        '''
        url: str = self._endpoint_url_range(stock_code, from_dt, to_dt)
        resp = self._http.request('GET', url)
        data: RawHistData = json.loads(resp.data.decode('utf-8'))
        hist_data: HistData = self._parse_hist_data(data)
        return TimeAndSalesDeliverData(start_date=from_dt, data=hist_data, dataname='TimeAndSalesDeliverData')

    def _parse_hist_data(self, hist_data: RawHistData) -> HistData:
        # [datetime, price, volume]
        parser = lambda x: [datetime.strptime(x[0], '%Y-%m-%d %H:%M:%S %z'), float(x[2]), float(x[1])]
        return list(map(parser, hist_data))


    def _endpoint_url_range(self, stock_code: str, from_dt: datetime, to_dt: datetime) -> str:
        from_str = from_dt.strftime('%Y-%m-%dT%H:%M:%S')
        to_str = to_dt.strftime('%Y-%m-%dT%H:%M:%S')
        return f'{self.protocol}://{self.host}:{self.port}/{stock_code}/{from_dt}/{to_dt}'

    def _dt_to_resp(self, stock_code: str,
            from_dt: datetime, to_dt: datetime) -> dict:
        return self.get_historical_data(stock_code, from_dt, to_dt)

class BinanceStore(object):
    '''
    データを処理してcelebroに渡しやすくする。そのために必要な接続情報や、gg
    '''
    # _GRANULARITIES = {
    #     (TimeFrame.Minutes, 1): KLINE_INTERVAL_1MINUTE,
    #     (TimeFrame.Minutes, 3): KLINE_INTERVAL_3MINUTE,
    #     (TimeFrame.Minutes, 5): KLINE_INTERVAL_5MINUTE,
    #     (TimeFrame.Minutes, 15): KLINE_INTERVAL_15MINUTE,
    #     (TimeFrame.Minutes, 30): KLINE_INTERVAL_30MINUTE,
    #     (TimeFrame.Minutes, 60): KLINE_INTERVAL_1HOUR,
    #     (TimeFrame.Minutes, 120): KLINE_INTERVAL_2HOUR,
    #     (TimeFrame.Minutes, 240): KLINE_INTERVAL_4HOUR,
    #     (TimeFrame.Minutes, 360): KLINE_INTERVAL_6HOUR,
    #     (TimeFrame.Minutes, 480): KLINE_INTERVAL_8HOUR,
    #     (TimeFrame.Minutes, 720): KLINE_INTERVAL_12HOUR,
    #     (TimeFrame.Days, 1): KLINE_INTERVAL_1DAY,
    #     (TimeFrame.Days, 3): KLINE_INTERVAL_3DAY,
    #     (TimeFrame.Weeks, 1): KLINE_INTERVAL_1WEEK,
    #     (TimeFrame.Months, 1): KLINE_INTERVAL_1MONTH,
    # }

    def __init__(self, api_key, api_secret, coin_refer, coin_target, testnet=False, retries=5):
        self.binance = Client(api_key, api_secret, testnet=testnet)
        self.binance_socket = ThreadedWebsocketManager(api_key, api_secret, testnet=testnet)
        self.binance_socket.daemon = True
        self.binance_socket.start()
        self.coin_refer = coin_refer
        self.coin_target = coin_target
        self.symbol = coin_refer + coin_target
        self.retries = retries

        self._cash = 0
        self._value = 0
        self.get_balance()

        self._step_size = None
        self._tick_size = None
        self.get_filters()

        self._broker = BinanceBroker(store=self)
        self._data = None
        
    def _format_value(self, value, step):
        precision = step.find('1') - 1
        if precision > 0:
            return '{:0.0{}f}'.format(value, precision)
        return floor(int(value))
        
    def retry(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, self.retries + 1):
                time.sleep(60 / 1200) # API Rate Limit
                try:
                    return func(self, *args, **kwargs)
                except (BinanceAPIException, ConnectTimeout, ConnectionError) as err:
                    if isinstance(err, BinanceAPIException) and err.code == -1021:
                        # Recalculate timestamp offset between local and Binance's server
                        res = self.binance.get_server_time()
                        self.binance.timestamp_offset = res['serverTime'] - int(time.time() * 1000)
                    
                    if attempt == self.retries:
                        raise
        return wrapper

    @retry
    def cancel_open_orders(self):
        orders = self.binance.get_open_orders(symbol=self.symbol)
        if len(orders) > 0:
            self.binance._request_api('delete', 'openOrders', signed=True, data={ 'symbol': self.symbol })

    @retry
    def cancel_order(self, order_id):
        try:
            self.binance.cancel_order(symbol=self.symbol, orderId=order_id)
        except BinanceAPIException as api_err:
            if api_err.code == -2011:  # Order filled
                return
            else:
                raise api_err
        except Exception as err:
            raise err
    
    @retry
    def create_order(self, side, type, size, price):
        params = dict()
        if type in [ORDER_TYPE_LIMIT, ORDER_TYPE_STOP_LOSS_LIMIT]:
            params.update({
                'timeInForce': TIME_IN_FORCE_GTC
            })
        if type != ORDER_TYPE_MARKET:
            params.update({
                'price': self.format_price(price)
            })

        return self.binance.create_order(
            symbol=self.symbol,
            side=side,
            type=type,
            quantity=self.format_quantity(size),
            **params)

    def format_price(self, price):
        return self._format_value(price, self._tick_size)
    
    def format_quantity(self, size):
        return self._format_value(size, self._step_size)

    @retry
    def get_asset_balance(self, asset):
        balance = self.binance.get_asset_balance(asset)
        return float(balance['free']), float(balance['locked'])

    def get_balance(self):
        free, locked = self.get_asset_balance(self.coin_target)
        self._cash = free
        self._value = free + locked

    def getbroker(self):
        return self._broker

    def getdata(self, timeframe_in_minutes, start_date=None):
        if not self._data:
            self._data = BinanceData(store=self, timeframe_in_minutes=timeframe_in_minutes, start_date=start_date)
        return self._data
        
    def get_filters(self):
        symbol_info = self.get_symbol_info(self.symbol)
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                self._step_size = f['stepSize']
            elif f['filterType'] == 'PRICE_FILTER':
                self._tick_size = f['tickSize']

    def get_interval(self, timeframe, compression):
        return self._GRANULARITIES.get((timeframe, compression))

    @retry
    def get_symbol_info(self, symbol):
        return self.binance.get_symbol_info(symbol)

    def stop_socket(self):
        self.binance_socket.stop()
        self.binance_socket.join(5)
