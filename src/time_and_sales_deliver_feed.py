# Original: 
# https://raw.githubusercontent.com/lindomar-oliveira/backtrader-binance/main/backtrader_binance/binance_feed.py
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

from operator import index
from typing import NewType, TypeAlias, Dict
from collections import deque

import pandas as pd
from datetime import datetime, date
import pytz

from backtrader.dataseries import TimeFrame
from backtrader.feed import DataBase
from backtrader.utils import date2num

State: TypeAlias = int
HistData: NewType = NewType('HistData', list[list[datetime, float]])
AlreadyCaluculatedPositions: NewType = NewType('AlreadyCaluculatedPositions', set)

class TimeAndSalesDeliverData(DataBase):
    params = (
        ('drop_newest', True),
        ('timeframe', TimeFrame.Ticks),
        ('tz', pytz.timezone('Asia/Tokyo')),
    )
    _ST_LIVE: State = 0
    _ST_HISTORBACK: State = 1
    _ST_OVER: State = 2

    def __init__(self, start_date=None, data: HistData=None):
        self.start_date = start_date
        self._data = deque()
        if data:
            self._hist_data = data
        self._interest_last_caluculated_date: date = date(1900, 1, 1)  # 金利を最後に計算した日付
        self._already_caluculated_positions: AlreadyCaluculatedPositions = set()  # 既に金利計算済みのポジション

    @property
    def interest_last_caluculated_date(self) -> date:
        ''' 金利を最後に計算した日付 '''
        return self._interest_last_caluculated_date

    @interest_last_caluculated_date.setter
    def interest_last_caluculated_date(self, date: date):
        ''' 金利を最後に計算した日付 '''
        self._interest_last_caluculated_date = date

    @property
    def already_caluculated_positions(self) -> AlreadyCaluculatedPositions:
        ''' 既に金利計算済みのポジション '''
        return self._already_caluculated_positions

    def start(self):
        DataBase.start(self)

        if self.start_date:
            self._state = self._ST_HISTORBACK
            self.put_notification(self.DELAYED)

            df = pd.DataFrame(self._hist_data,
                    columns=['datetime', 'price', 'volume'])
            df.index = df.datetime
            self._data.extend(df.values.tolist())            
        else:
            self._start_live()

    def _load(self):
        try:
            line = self._data.popleft()
        except IndexError:
            return None
        dt, price, volume = line
        # date2num: https://github.com/mementum/backtrader/blob/0fa63ef4a35dc53cc7320813f8b15480c8f85517/backtrader/utils/dateintern.py#L202
        # main.py 中のロガーから、linebuffer.datetime()が呼ばれるので、floatの日時表示にする必要がある。
        # datetime: https://github.com/mementum/backtrader/blob/e2674b1690f6366e08646d8cfd44af7bb71b3970/backtrader/linebuffer.py#L386-L388
        self.lines.datetime[0] = date2num(dt)
        self.lines.open[0] = price
        self.lines.high[0] = price
        self.lines.low[0] = price
        self.lines.close[0] = price
        self.lines.volume[0] = volume
        return True



class BinanceData(DataBase):
    params = (
        ('drop_newest', True),
    )
    
    # States for the Finite State Machine in _load
    _ST_LIVE, _ST_HISTORBACK, _ST_OVER = range(3)

    def __init__(self, store, timeframe_in_minutes, start_date=None):
        self.timeframe_in_minutes = timeframe_in_minutes
        self.start_date = start_date

        self._store = store
        self._data = deque()

    def _handle_kline_socket_message(self, msg):
        """https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams"""
        if msg['e'] == 'kline':
            if msg['k']['x']:  # Is closed
                kline = self._parser_to_kline(msg['k']['t'], msg['k'])
                self._data.extend(kline.values.tolist())
        elif msg['e'] == 'error':
            raise msg

    def _load(self):
        if self._state == self._ST_OVER:
            return False
        elif self._state == self._ST_LIVE:
            return self._load_kline()
        elif self._state == self._ST_HISTORBACK:
            if self._load_kline():
                return True
            else:
                self._start_live()

    def _load_kline(self):
        try:
            kline = self._data.popleft()
        except IndexError:
            return None

        timestamp, open_, high, low, close, volume = kline

        self.lines.datetime[0] = date2num(timestamp)
        self.lines.open[0] = open_
        self.lines.high[0] = high
        self.lines.low[0] = low
        self.lines.close[0] = close
        self.lines.volume[0] = volume
        return True
    
    def _parser_dataframe(self, data):
        df = data.copy()
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df['timestamp'] = df['timestamp'].values.astype(dtype='datetime64[ms]')
        df['open'] = df['open'].values.astype(float)
        df['high'] = df['high'].values.astype(float)
        df['low'] = df['low'].values.astype(float)
        df['close'] = df['close'].values.astype(float)
        df['volume'] = df['volume'].values.astype(float)
        # df.set_index('timestamp', inplace=True)
        return df
    
    def _parser_to_kline(self, timestamp, kline):
        df = pd.DataFrame([[timestamp, kline['o'], kline['h'],
                            kline['l'], kline['c'], kline['v']]])
        return self._parser_dataframe(df)
    
    def _start_live(self):
        self._state = self._ST_LIVE
        self.put_notification(self.LIVE)
            
        self._store.binance_socket.start_kline_socket(
            self._handle_kline_socket_message,
            self.symbol_info['symbol'],
            self.interval)
        
    def haslivedata(self):
        return self._state == self._ST_LIVE and self._data

    def islive(self):
        return True
        
    def start(self):
        DataBase.start(self)

        self.interval = self._store.get_interval(TimeFrame.Minutes, self.timeframe_in_minutes)
        if self.interval is None:
            self._state = self._ST_OVER
            self.put_notification(self.NOTSUPPORTED_TF)
            return
        
        self.symbol_info = self._store.get_symbol_info(self._store.symbol)
        if self.symbol_info is None:
            self._state = self._ST_OVER
            self.put_notification(self.NOTSUBSCRIBED)
            return

        if self.start_date:
            self._state = self._ST_HISTORBACK
            self.put_notification(self.DELAYED)

            klines = self._store.binance.get_historical_klines(
                self.symbol_info['symbol'],
                self.interval,
                self.start_date.strftime('%d %b %Y %H:%M:%S'))

            if self.p.drop_newest:
                klines.pop()
            
            df = pd.DataFrame(klines)
            df.drop(df.columns[[6, 7, 8, 9, 10, 11]], axis=1, inplace=True)  # Remove unnecessary columns
            df = self._parser_dataframe(df)
            self._data.extend(df.values.tolist())            
        else:
            self._start_live()
