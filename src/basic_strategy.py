import backtrader as bt
from backtrader import Order, OrderBase

import pytz

from logging import getLogger, StreamHandler, FileHandler, \
     Formatter, DEBUG, INFO, WARN


class BasicStrategy(bt.Strategy):
    params = (
        ('tick_counter', 0),
        ('size', 100),
        ('smaperiod', 5),
        ('log_name', 'basic_strategy.log'),
        ('log_mode', 'w'),
    )
    def _log(self, txt, loglevel=INFO, dt=None):
        ''' Logging function for this strategy '''
        # self.datas[0].datetime.datetime() は、
        # 内部的に linebuffer.datetime() を呼び出す
        # https://github.com/mementum/backtrader/blob/e2674b1690f6366e08646d8cfd44af7bb71b3970/backtrader/linebuffer.py#L386-L388
        dt = dt or self.datas[0].datetime.datetime(
            ago=0, tz=pytz.timezone('Asia/Tokyo'))
        self._logger.log(loglevel, '%s [%6d], %s' % (dt.isoformat(), self.p.tick_counter, txt))

    def _debug(self, txt, dt=None):
        self._log(txt, DEBUG, dt)

    def _info(self, txt, dt=None):
        self._log(txt, INFO, dt)

    def __init__(self, loglevel=DEBUG):
        # Keep a reference to the "close" line in the data[0] dataseries
        self._dataclose = self.datas[0].close
        self._setup_logger(loglevel)
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.smaperiod)
        self._cash = 0
        self._value = 0


    def notify_order(self, order: Order) -> None:
        '''
        Backtraderから呼ばれる
        - Submitted: sent to the broker and awaiting confirmation
        - Accepted: accepted by the broker
        - Partial: partially executed
        - Completed: fully exexcuted
        - Canceled/Cancelled: canceled by the user
        - Expired: expired
        - Margin: not enough cash to execute the order.
        - Rejected: Rejected by the broker
        '''
        # https://www.backtrader.com/docu/order/#:~:text=of%20an%20order-,Order%20Status%20values,-The%20following%20are
        if order.status == Order.Accepted:
            # Brokerが注文受領
            self._debug('Accepted: [%s] %.2f * %d' %
                (self._buy_sell_in_str(order),
                 order.price or 0, order.size or 0))
        elif order.status == Order.Completed:
            # 注文が通った
            executed = order.executed
            self._info('Completed: [%s]: %.2f * %d' %
                (self._buy_sell_in_str(order),
                 executed.price, executed.size))
        elif order.status in \
            (Order.Canceled, Order.Expired, Order.Margin, Order.Rejected):
            self._debug('Completed: [%s]: %.2f * %d' %
                (self._buy_sell_in_str(order),
                 executed.price, executed.size))
            # 注文が通らなかった
            import pdb; pdb.set_trace()  # FIXME: WIP
    def notify_cashvalue(self, cash: float, value: float):
        '''
        Parameters
        --------------
        cash: float
            現金
        value: float
            時価総額
        '''
        self._debug(f'notify_cashvalue(cash={cash:9,} / value={value:9,})')
        [self._cash, self._value] = cash, value
        return

    def next(self):
        self.p.tick_counter += 1
        # 今カーソルがある日時のtickにおける売買成立値
        self._debug('[%6d] [Close] = %.2f' %
            (self.p.tick_counter, self._dataclose[0]))

        # もし5本連続で下がっているなら
        if self.p.tick_counter >= 5 and \
           self._is_falling_over_5_ticks():
            # 1ティック前の値で売り注文（当日限り有効）
            price = self._dataclose[-1]
            size = self.p.size
            self._info('Order: [sell] %.2f * %d' % (price, size))
            self.sell(size=size, price=price, valid=Order.DAY)

    def stop(self):
        '''終了時にはファイルをクローズする。Backtraderから呼ばれる。'''
        self.fhandler.close()

    def _is_falling_over_5_ticks(self) -> bool:
        '''
        Returns
        --------------- 
            もし5本連続で下がっているならTrue
        '''
        return self._dataclose[0] < self._dataclose[-1] < \
           self._dataclose[-2] < self._dataclose[-3] < self._dataclose[-4]

    def _buy_sell_in_str(self, order: Order) -> str:
        '''
        Returns
        ---------------
        与えた order が 'buy' or 'sell' を返す。
        '''
        return OrderBase.OrdTypes[order.ordtype]

        # if order.isbuy():
        #     return 'buy'
        # elif order.issell():
        #     return 'sell'
        # else:
        #     raise 'Unknown type'

    def _status_in_str(self, order: Order) -> str:
        '''
        Returns
        ---------------
        与えた order の status を str で返す。
        '''
        return OrderBase.Status[order.status]

    def _setup_logger(self, loglevel):
        formatter = Formatter('[%(levelname)5s] %(message)s')
        self._logger = getLogger(__name__)
        self.handler = StreamHandler()
        self.handler.setLevel(loglevel)
        self.handler.setFormatter(formatter)
        self.fhandler = FileHandler(
            self.p.log_name, mode=self.p.log_mode, encoding='utf-8')
        self.fhandler.setLevel(loglevel)
        self.fhandler.setFormatter(formatter)
        self._logger.setLevel(DEBUG)
        self._logger.addHandler(self.handler)
        self._logger.addHandler(self.fhandler)
        self._logger.propagate = False