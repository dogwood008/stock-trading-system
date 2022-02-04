# Original: 
# https://github.com/lindomar-oliveira/backtrader-binance/blob/c3ea500d453ec16f925450c299be097bf99970e2/backtrader_binance/binance_broker.py
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

import datetime as dt

from collections import defaultdict, deque
from math import copysign

from backtrader.broker import BrokerBase
from backtrader.order import Order, OrderBase
from backtrader.position import Position

class TimeAndSaledDeliverEnum:
    SIDE_BUY = 'side_buy'



class TimeAndSalesDeliverBroker(OrderBase):
    def __init__(self, owner, data, exectype, order):
        self.owner = owner
        self.data = data
        self.exectype = exectype
        self.ordtype = self.Buy if order['side'] == TimeAndSaledDeliverEnum.SIDE_BUY else self.Sell

class BinanceOrder(OrderBase):
    def __init__(self, owner, data, exectype, binance_order):
        self.owner = owner
        self.data = data
        self.exectype = exectype
        self.ordtype = self.Buy if binance_order['side'] == SIDE_BUY else self.Sell
        
        # Market order price is zero
        if self.exectype == Order.Market:
            self.size = float(binance_order['executedQty'])
            self.price = sum(float(fill['price']) for fill in binance_order['fills']) / len(binance_order['fills'])  # Average price
        else:
            self.size = float(binance_order['origQty'])
            self.price = float(binance_order['price'])
        self.binance_order = binance_order
        
        super(BinanceOrder, self).__init__()
        self.accept()


class BinanceBroker(BrokerBase):
    ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET, ORDER_TYPE_STOP_LOSS, ORDER_TYPE_STOP_LOSS_LIMIT = range(4)
    _ORDER_TYPES = {
        Order.Limit: ORDER_TYPE_LIMIT,
        Order.Market: ORDER_TYPE_MARKET,
        Order.Stop: ORDER_TYPE_STOP_LOSS,
        Order.StopLimit: ORDER_TYPE_STOP_LOSS_LIMIT,
    }

    def __init__(self, store):
        super(BinanceBroker, self).__init__()

        self.notifs = deque()
        self.positions = defaultdict(Position)

        self.open_orders = list()
    
        self._store = store
        self._store.binance_socket.start_user_socket(self._handle_user_socket_message)

    def _execute_order(self, order, date, executed_size, executed_price):
        order.execute(
            date,
            executed_size,
            executed_price,
            0, 0.0, 0.0,
            0, 0.0, 0.0,
            0.0, 0.0,
            0, 0.0)
        pos = self.getposition(order.data, clone=False)
        pos.update(copysign(executed_size, order.size), executed_price)

    def _handle_user_socket_message(self, msg):
        """https://binance-docs.github.io/apidocs/spot/en/#payload-order-update"""
        if msg['e'] == 'executionReport':
            if msg['s'] == self._store.symbol:
                for o in self.open_orders:
                    if o.binance_order['orderId'] == msg['i']:
                        if msg['X'] in [ORDER_STATUS_FILLED, ORDER_STATUS_PARTIALLY_FILLED]:
                            date = dt.datetime.fromtimestamp(msg['T'] / 1000)
                            executed_size = float(msg['l'])
                            executed_price = float(msg['L'])
                            self._execute_order(o, dt, executed_size, executed_price)
                        self._set_order_status(o, msg['X'])

                        if o.status not in [Order.Accepted, Order.Partial]:
                            self.open_orders.remove(o)
                        self.notify(o)
        elif msg['e'] == 'error':
            raise msg
    
    def _set_order_status(self, order, binance_order_status):
        if binance_order_status == ORDER_STATUS_CANCELED:
            order.cancel()
        elif binance_order_status == ORDER_STATUS_EXPIRED:
            order.expire()
        elif binance_order_status == ORDER_STATUS_FILLED:
            order.completed()
        elif binance_order_status == ORDER_STATUS_PARTIALLY_FILLED:
            order.partial()
        elif binance_order_status == ORDER_STATUS_REJECTED:
            order.reject()

    def _submit(self, owner, data, side, exectype, size, price):
        type = self._ORDER_TYPES.get(exectype, ORDER_TYPE_MARKET)

        binance_order = self._store.create_order(side, type, size, price)
        order = BinanceOrder(owner, data, exectype, binance_order)
        if binance_order['status'] in [ORDER_STATUS_FILLED, ORDER_STATUS_PARTIALLY_FILLED]:
            self._execute_order(
                order,
                dt.datetime.fromtimestamp(binance_order['transactTime'] / 1000),
                float(binance_order['executedQty']),
                float(binance_order['price']))
        self._set_order_status(order, binance_order['status'])
        if order.status == Order.Accepted:
            self.open_orders.append(order)
        self.notify(order)
        return order

    def buy(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            **kwargs):
        return self._submit(owner, data, SIDE_BUY, exectype, size, price)

    def cancel(self, order):
        order_id = order.binance_order['orderId']
        self._store.cancel_order(order_id)
        
    def format_price(self, value):
        return self._store.format_price(value)

    def get_asset_balance(self, asset):
        return self._store.get_asset_balance(asset)

    def getcash(self):
        self.cash = self._store._cash
        return self.cash

    def get_notification(self):
        if not self.notifs:
            return None

        return self.notifs.popleft()

    def getposition(self, data, clone=True):
        pos = self.positions[data._dataname]
        if clone:
            pos = pos.clone()
        return pos

    def getvalue(self, datas=None):
        self.value = self._store._value
        return self.value

    def notify(self, order):
        self.notifs.append(order)

    def sell(self, owner, data, size, price=None, plimit=None,
             exectype=None, valid=None, tradeid=0, oco=None,
             trailamount=None, trailpercent=None,
             **kwargs):
        return self._submit(owner, data, SIDE_SELL, exectype, size, price)
