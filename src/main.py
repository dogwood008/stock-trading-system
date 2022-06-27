# from __future__ import (absolute_import, division, print_function,
#                        unicode_literals)

from datetime import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])


# Import the backtrader platform
import backtrader as bt
from backtrader import Order

from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
from kabu_s_logger import KabuSLogger

sys.path.append(os.path.join(os.path.dirname(__file__), '.'))
#from time_and_sales_deliver_store import TimeAndSalesDeliverStore
from time_and_sales_deliver_store import TimeAndSalesDeliverStore
from basic_strategy import BasicStrategy
from dmm_kabu_comission import DMMKabuComission

# ログ用
from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN

# Create a Stratey
if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    IN_DEVELOPMENT = True
    loglevel = DEBUG if IN_DEVELOPMENT else WARN
    cerebro.addstrategy(BasicStrategy, loglevel)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    # modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # datapath = os.path.join(modpath, '/opt/backtrader/datas/orcl-1995-2014.txt')

    # Create a Data Feed
    # data = bt.feeds.TimeAndSalesDeliverData(
    #     dataname=datapath,
    #     # Do not pass values before this date
    #     fromdate=datetime.datetime(2000, 1, 1),
    #     # Do not pass values after this date
    #     todate=datetime.datetime(2000, 12, 31),
    #     reverse=False)
    stock_code: str = '7974'
    options = { 'protocol': 'http', 'host': 'localhost', 'port': '4567' }  # FIXME: give some args
    store = TimeAndSalesDeliverStore(**options)
    start_dt = datetime.strptime('2021-11-01T09:00:00', "%Y-%m-%dT%H:%M:%S")
    end_dt = datetime.strptime('2021-11-30T15:00:00', "%Y-%m-%dT%H:%M:%S")
    data = store.getdata(stock_code=stock_code, start_dt=start_dt, end_dt=end_dt)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000.0 * 10000)
    dataname = 'TimeAndSalesDeliverData'
    logger = KabuSLogger()
    handler = StreamHandler(sys.stdout)
    handler.setLevel(loglevel)
    logger.addHandler(handler)
    cerebro.broker.addcommissioninfo(DMMKabuComission(logger), name=dataname)

    # https://www.backtrader.com/blog/posts/2016-12-06-shorting-cash/shorting-cash/
    # cerebro.broker.set_shortcash(False)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    b = Bokeh(style='bar', plot_mode='single', scheme=Tradimo(), output_mode='save', filename='chart.html')
    cerebro.plot(b)