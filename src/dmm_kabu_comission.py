from datetime import datetime
import backtrader as bt
from kabu_s_logger import KabuSLogger

from typing import NewType, Dict

from time_and_sales_deliver_feed import TimeAndSalesDeliverData

AlreadyCaluculatedPositions: NewType = NewType('AlreadyCaluculatedPositions', Dict[str, str])
class DMMKabuComission(bt.CommInfoBase):
    DAYS_IN_A_YEAR = 365.0
    params = (
      ('commission', 88.0),
      ('commtype', bt.CommInfoBase.COMM_FIXED),
      ('stocklike', False),
      # https://kabu.dmm.com/commission/
      ('buy_interest', .027),  # 2.7%
      ('sell_interest', .011),  # 1.1%
      ('interest_long', True),
      ('stocklike', True),  # 信用取引
    )

    def __init__(self, logger: KabuSLogger=None):
      self._logger: KabuSLogger = logger if logger else KabuSLogger()
      self._stocklike = self.p.stocklike
      self._interest_last_caluculated_date: datetime = datetime(1900, 1, 1)  # 金利を最後に計算した日付
      self._already_caluculated_positions: AlreadyCaluculatedPositions = {}  # 既に金利計算済みのポジション

    def _debug(self, msg):
      if self._logger:
        self._logger.debug(msg)
        print(msg)

    def _position_id(self, pos: bt.position.Position) -> str:
      return '{}_{}'.format(pos.datetime.isoformat(), pos.size)

    def get_credit_interest(self, data, pos, dt) -> float:
      '''Calculates the credit due for short selling or product specific'''
      size, price = pos.size, pos.price

      dt0 = dt.date()
      dt1 = pos.datetime.date()
      self._debug('dt0(dt): {}, dt1(dt): {}'.format(dt, pos.datetime))

      # 信用買い／売りした日を1日目とする
      days = (dt0 - dt1).days + 1
      interest_percentage: float = (self.p.buy_interest \
        if size > 0 else self.p.sell_interest) / self.DAYS_IN_A_YEAR
      
      is_the_date_next_day = data.interest_last_caluculated_date < dt0

      if is_the_date_next_day: # 日付が変わったら
        data.interest_last_caluculated_date = dt0
        data.already_caluculated_positions.clear()
      elif self._is_already_interest_caluculated(pos, data):   # 既に金利計算済みなら
        self._debug('already caluculated: {}'.format(self._position_id(pos)))
        return 0.0

      interest_price: float = days * interest_percentage * abs(size) * price
      self._debug('interest_price: {}'.format(interest_price))
      data.already_caluculated_positions.add(self._position_id(pos))
      return interest_price

    def _is_already_interest_caluculated(
        self, pos: bt.position.Position, data: TimeAndSalesDeliverData) -> bool:
      ''' 既に金利計算済みならTrueを返す '''
      # https://stackoverflow.com/a/39582288/15983717
      return self._position_id(pos) in data._already_caluculated_positions

    def _get_credit_interest(self, data, size, price, days, dt0, dt1):
      # ここに到達するなら、オーバーライドに失敗している
      raise NotImplementedError

    def _getcommission(self, size, price, pseudoexec):
      '''Calculates the commission of an operation at a given price

      pseudoexec: if True the operation has not yet been executed
      '''
      # 1約定毎300万円超で手数料0円、以下で88円
      return 0.0 if price * abs(size) > 300 * 10000 else self.p.comission