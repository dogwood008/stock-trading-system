from typing import Callable
import backtrader as bt
from backtrader import Order, OrderBase

import pytz

from logging import getLogger, StreamHandler, FileHandler, \
     Formatter, DEBUG, INFO, WARN


class BasicStrategy(bt.Strategy):
    NOT_GIVEN:int = -1
    MARKET_ORDER_PRICE = None
    CLOSE_POSITION_ORDER_PRICE = None

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
        if order.status == Order.Completed:
            # 注文が通った
            executed = order.executed
            self._info('%9s: [%s]: %.2f * %d' %
                (self._status_in_str(order),
                 self._buy_sell_in_str(order),
                 executed.price, executed.size))
        else:
            # 注文が通らなかった 他
            self._debug('%9s: [%s]: %.2f * %d' %
                (self._status_in_str(order),
                 self._buy_sell_in_str(order),
                 order.price or 0, order.size or 0))

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
        ''' ティック毎に呼ばれる '''
        self.p.tick_counter += 1
        # 今カーソルがある日時のtickにおける売買成立値
        self._debug('[Close] = %.2f' %
            self._dataclose[0])

        n_threshold: int = 10
        # もしn本連続で上がっているなら
        if self.p.tick_counter >= n_threshold and \
           self._is_increasing_over_n_ticks(n=n_threshold):
            if self._is_holding_positions():
                self._close_operation()
            else:
                self._buy_operation(price=self._dataclose[0])

        # もしn本連続で下がっているなら
        if self.p.tick_counter >= n_threshold and \
           self._is_falling_over_n_ticks(n=n_threshold):
            if self._is_holding_positions():
                self._close_operation()
            else:
                self._sell_operation(price=self._dataclose[0])

    def stop(self):
        '''終了時にはファイルをクローズする。Backtraderから呼ばれる。'''
        self.fhandler.close()

    def _close_operation(self):
        position: bt.position.Position = self.position
        size: int = position.size
        # https://github.com/mementum/backtrader/blob/e22205427bc0ac55723677c88573737a172590ef/backtrader/position.py#L130-L132
        if not size: return
        is_buy_position: bool = size > 0
        reverse_op: Callable = \
            self._sell_operation if is_buy_position else self._buy_operation
        reverse_op(size=size, price=self.CLOSE_POSITION_ORDER_PRICE)

    def _buy_operation(self, size: int=MARKET_ORDER_PRICE, price: float=None):
        '''
        1ティック前の値で買い注文（当日限り有効）

        Parameters
        ---------------
        size: int
            数量
        price: float
            価格　Noneで成行
        '''
        size = size or self.p.size
        # self._info('Order: [sell] %.2f * %d' % (price, size))
        self.buy(size=size, price=price, valid=Order.DAY)

    def _is_holding_positions(self) -> bool:
        '''
        Returns
        ---------------
            もし建玉があれば、True
        '''
        return bool(self.position.size)


    def _is_increasing_over_n_ticks(self, n: int) -> bool:
        '''
        Returns
        ---------------
            もしn本連続で上がっているならTrue
        '''
        return all(map(
            lambda x: self._dataclose[-x] >= self._dataclose[-(x+1)],
            range(n)))

    def _is_falling_over_n_ticks(self, n: int) -> bool:
        '''
        Returns
        --------------- 
            もしn本連続で下がっているならTrue
        '''
        return all(map(
            lambda x: self._dataclose[-x] <= self._dataclose[-(x+1)],
            range(n)))

    def _sell_operation(self, size: int=MARKET_ORDER_PRICE, price: float=None):
        '''
        1ティック前の値で売り注文（当日限り有効）

        Parameters
        ---------------
        size: int
            数量
        price: float
            価格　Noneで成行
        '''
        size = size or self.p.size
        # self._info('Order: [sell] %.2f * %d' % (price, size))
        self.sell(size=size, price=price, valid=Order.DAY)

    def _buy_sell_in_str(self, order: Order) -> str:
        '''
        Returns
        ---------------
        与えた order が 'buy' or 'sell' を返す。
        '''
        return OrderBase.OrdTypes[order.ordtype]

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