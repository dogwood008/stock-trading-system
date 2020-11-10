# from __future__ import (absolute_import, division, print_function,
#                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt
from backtrader import Order

from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo

# ログ用
from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN

# Create a Stratey
class TestStrategyWithLogger(bt.Strategy):
    params = (
        ('size', 1000),
        ('smaperiod', 5),
    )
    def _log(self, txt, loglevel=INFO, dt=None):
        ''' Logging function for this strategy '''
        dt = dt or self.datas[0].datetime.date(0)
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
        self._debug('[Close, position] = %.2f, %s' % (self._dataclose[0], self.getposition()))

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

if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    IN_DEVELOPMENT = True
    loglevel = DEBUG if IN_DEVELOPMENT else WARN
    cerebro.addstrategy(TestStrategyWithLogger, loglevel)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '/opt/backtrader/datas/orcl-1995-2014.txt')

    # Create a Data Feed
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2000, 12, 31),
        reverse=False)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    b = Bokeh(style='bar', plot_mode='single', scheme=Tradimo(), output_mode='save', filename='chart.html')
    cerebro.plot(b)
