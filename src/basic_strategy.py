import backtrader as bt
from backtrader import Order

import pytz

from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN

class BasicStrategy(bt.Strategy):
    params = (
        ('size', 1000),
        ('smaperiod', 5),
    )
    def _log(self, txt, loglevel=INFO, dt=None):
        ''' Logging function for this strategy '''
        # self.datas[0].datetime.datetime() は、
        # 内部的に linebuffer.datetime() を呼び出す
        # https://github.com/mementum/backtrader/blob/e2674b1690f6366e08646d8cfd44af7bb71b3970/backtrader/linebuffer.py#L386-L388
        dt = dt or self.datas[0].datetime.datetime(
            ago=0, tz=pytz.timezone("Asia/Tokyo"))
        self._logger.log(loglevel, '%s, %s' % (dt.isoformat(), txt))

    def _debug(self, txt, dt=None):
        self._log(txt, DEBUG, dt)

    def _info(self, txt, dt=None):
        self._log(txt, INFO, dt)

    def __init__(self, loglevel=DEBUG):
        # Keep a reference to the "close" line in the data[0] dataseries
        self._dataclose = self.datas[0].close
        self._logger = getLogger(__name__)
        self.handler = StreamHandler()
        self.handler.setLevel(loglevel)
        self._logger.setLevel(DEBUG)
        self._logger.addHandler(self.handler)
        self._logger.propagate = False
        self.handler.setFormatter(
                Formatter('[%(levelname)s] %(message)s'))
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.smaperiod)


    def notify_order(self, order: Order) -> None:
        ''' backtraderから呼ばれる '''
        if order.status == Order.Completed:
            if order.isbuy():
                self._info('BUY: %.2f' % order.executed.price)

    def next(self):
        # Simply log the closing price of the series from the reference
        self._debug('[Close] = %.2f' % (self._dataclose[0]))

        if self._dataclose[0] < self._dataclose[-1]:
            # current close less than previous close

            if self._dataclose[-1] < self._dataclose[-2]:
                # previous close less than the previous close

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self._info('BUY CREATE, %.2f' % self._dataclose[0])
                self.buy(size=self.params.size)

            if self._dataclose[-2] * .97 > self._dataclose[-1]:
                # 前日が前々日の3%を超える下落時に手仕舞い
                self.close()