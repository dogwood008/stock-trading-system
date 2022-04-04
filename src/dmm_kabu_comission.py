import backtrader as bt

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
    )

    def get_credit_interest(self, _data, pos, dt):
        '''Calculates the credit due for short selling or product specific'''
        size, price = pos.size, pos.price

        dt0 = dt.date()
        dt1 = pos.datetime.date()

        # 信用買い／売りした日を1日目とする
        days = (dt0 - dt1).days + 1
        interest = (self.p.buy_interest \
          if size > 0 else self.p.sell_interest) / self.DAYS_IN_A_YEAR
        return days * interest * abs(size) * price

    def _get_credit_interest(self, data, size, price, days, dt0, dt1):
        # ここに到達するなら、オーバーライドに失敗している
        raise NotImplementedError

    def _getcommission(self, size, price, pseudoexec):
        '''Calculates the commission of an operation at a given price

        pseudoexec: if True the operation has not yet been executed
        '''
        # 1約定毎300万円超で手数料0円、以下で88円
        return 0.0 if price * abs(size) > 300 * 10000 else self.p.comission