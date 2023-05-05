from datetime import datetime
import backtrader as bt
from kabu_s_logger import KabuSLogger

from typing import NewType, Dict
from logging import DEBUG, INFO

from time_and_sales_deliver_feed import TimeAndSalesDeliverData

AlreadyCaluculatedPositions: NewType = NewType('AlreadyCaluculatedPositions', Dict[str, str])
class AuKabucomOneshotsComission(bt.CommInfoBase):
    DAYS_IN_A_YEAR = 365.0
    params = (
      ('commission', None),
      ('commtype', bt.CommInfoBase.COMM_FIXED),
      ('stocklike', False),
      # https://kabu.com/cost/default.html
      # https://kabu.com/item/shinyo/cost.html#anc07
      ('buy_interest', .0298),  # 2.98%
      ('sell_interest', .0115),  # 1.15%
      ('dailytrade_interest', .0180),  # 1.80%
      ('interest_long', True),
      ('stocklike', True),  # 信用取引
      ('dailytrade', True),  # デイトレ信用
    )

    def __init__(self, logger: KabuSLogger=None):
      self._logger: KabuSLogger = logger if logger else KabuSLogger()
      self._stocklike = self.p.stocklike
      self._interest_last_caluculated_date: datetime = datetime(1900, 1, 1)  # 金利を最後に計算した日付
      self._already_caluculated_positions: AlreadyCaluculatedPositions = {}  # 既に金利計算済みのポジション

    def _log(self, txt, loglevel=INFO, dt=None):
        ''' Logging function for this strategy '''
        self._logger.log(loglevel, '%s, %s' % (dt.isoformat(), txt))

    def _debug(self, txt, dt=None):
        self._log(txt, DEBUG, dt)

    def _info(self, txt, dt=None):
        self._log(txt, INFO, dt)

    def _position_id(self, pos: bt.position.Position) -> int:
      return id(pos)

    def _base_interest(self, pos: bt.position.Position) -> float:
      size, price = pos.size, pos.price
      value: float = price * size
      if self.p.dailytrade:
        return 0.0 if value >= 100 * 10000 else self.p.dailytrade_interest

      is_buy, is_sell = pos.size > 0, pos.size < 0
      if is_buy:
        interest_base: float = self.p.buy_interest
      elif is_sell:
        interest_base: float = self.p.sell_interest


    # backtrader.CommInfoBase.get_credit_interest()をオーバーライド
    # https://github.com/mementum/backtrader/blob/e2674b1690f6366e08646d8cfd44af7bb71b3970/backtrader/comminfo.py#L258-L272
    # ここから呼ばれる: https://github.com/mementum/backtrader/blob/0fa63ef4a35dc53cc7320813f8b15480c8f85517/backtrader/brokers/bbroker.py#L1189
    def get_credit_interest(self, data, pos, current_dt) -> float:
      '''Calculates the credit due for short selling or product specific'''
      size, price = pos.size, pos.price

      current_date = current_dt.date()  # カーソルのあるDateTime
      position_date = pos.datetime.date()  # 建玉の作成DateTime
      self._debug('current_dt(dt): {}, position_dt(dt): {}'.format(current_dt, pos.datetime), current_dt)

      # 信用買い／売りした日を1日目とする
      days = (current_date - position_date).days + 1

      # 日利
      interest_percentage: float = self._base_interest(pos) / self.DAYS_IN_A_YEAR
      
      # 日付けが変わったor金利未計上
      is_to_pay_interests: bool = data.interest_last_caluculated_date < current_date

      if is_to_pay_interests: # 金利を計上する必要がある場合
        data.interest_last_caluculated_date = current_date
        data.already_caluculated_positions.clear()

      interest_price: float = days * interest_percentage * abs(size) * price
      position_id: int = self._position_id(pos)

      if self._is_already_interest_caluculated(pos, data):   # 既に金利計算済みなら
        self._debug('[Comission/Paid] position_id: {}' \
          .format(position_id), dt=current_dt)
        return 0.0

      self._debug('[Comission] interest_price: {} / position_id: {}' \
        .format(interest_price, position_id), dt=current_dt)
      data.already_caluculated_positions.add(position_id)
      return interest_price

    def _is_already_interest_caluculated(
        self, pos: bt.position.Position, data: TimeAndSalesDeliverData) -> bool:
      ''' 既に金利計算済みならTrueを返す '''
      # https://stackoverflow.com/a/39582288/15983717
      return self._position_id(pos) in data._already_caluculated_positions

    def _get_credit_interest(self, data, size, price, days, dt0, dt1):
      # ここに到達するなら、オーバーライドに失敗している
      raise NotImplementedError

    def _getcommission(self, size, price, pseudoexec) -> float:
      '''Calculates the commission of an operation at a given price

      pseudoexec: if True the operation has not yet been executed
      '''
      value: float = price * size
      if self.p.dailytrade or self.p.stocklike:
        return 0.0

      if value <= 5 * 10000:
        return 55.0
      if value <= 10 * 10000:
        return 99.0
      if value <= 20 * 10000:
        return 115.0
      if value <= 50 * 10000:
        return 275.0
      if value <= 100 * 10000:
        return 535.0
      else:
        return min(value * 0.00099 + 99, 4059.0)
