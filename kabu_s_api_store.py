#!/usr/bin/env python
# coding: utf-8

# %%: Set stylesheet if in Jupyter
# https://recruit-tech.co.jp/blog/2018/10/16/jupyter_notebook_tips/
def set_stylesheet():
    try:
        from IPython.display import display, HTML
        css = get_ipython().getoutput('wget https://raw.githubusercontent.com/lapis-zero09/jupyter_notebook_tips/master/css/jupyter_notebook/monokai.css -q -O -')
        css = "\n".join(css)
        display(HTML('<style type="text/css">%s</style>'%css))
    except:
        pass
set_stylesheet()



# %%: Define class KabuSAPIStore
from backtrader.store import MetaSingleton
from backtrader.utils.py3 import queue, with_metaclass

import kabusapi
import backtrader as bt

import collections
import threading

from datetime import timedelta

from logging import DEBUG, INFO
from kabu_s_logger import KabuSLogger
from kabu_s_api_env import KabuSAPIEnv

if 'KabuSAPIStore' in globals():
    del KabuSAPIStore
class KabuSAPIStore(with_metaclass(MetaSingleton, object)):
    '''Singleton class wrapping to control the connections to Kabu STATION API.

    Params:

      - ``token`` (default:``None``): API access token

      - ``account`` (default: ``None``): account id

      - ``practice`` (default: ``False``): use the test environment

      - ``account_tmout`` (default: ``10.0``): refresh period for account
        value/cash refresh
    '''

    BrokerCls = None  # broker class will autoregister
    DataCls = None  # data class will auto register

    params = (
        ('host', 'localhost'),
        ('env', KabuSAPIEnv.DEV),
        ('port', None),
        ('password', None),
        ('logger', None),
        ('handler', None),
        ('headers', {}),
        ('token', None),
    )

    # _DTEPOCH = datetime(1970, 1, 1)
    # _ENVPRACTICE = 'practice'
    # _ENVLIVE = 'live'

    @classmethod
    def getdata(cls, *args, **kwargs):
        '''Returns ``DataCls`` with args, kwargs'''
        return cls.DataCls(*args, **kwargs)

    @classmethod
    def getbroker(cls, *args, **kwargs):
        '''Returns broker with *args, **kwargs from registered ``BrokerCls``'''
        return cls.BrokerCls(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        def _getport() -> int:
            if self.p.port:
                return port
            return 18081 if self.p.env == KabuSAPIEnv.DEV else 18080

        def _init_kabusapi_client(
            token: str=None, headers: dict={}) -> kabusapi.Context:
            host = self.p.host
            port = self.p.port or _getport()
            password = self.p.password
            if not token:
                token = kabusapi.Context(host, port, password).token
            self.kapi = kabusapi.Context(host, port, token=token)
            for k, v in headers.items():
                self.kapi._set_header(k, v)
            self._logger.debug('_init_kabusapi_client() called')
            
        super(KabuSAPIStore, self).__init__()

        if self.p.logger:
            self._logger = self.p.logger
        else:
            loglevel = DEBUG if self.p.env == KabuSAPIEnv.DEV else INFO
            self._logger: KabuSLogger = KabuSLogger(__name__,
                                       loglevel_logger=loglevel)
            if self.p.handler:
                self._logger.addHandler(self.p.handler)

        self.notifs = collections.deque()  # store notifications for cerebro

        self._env = None  # reference to cerebro for general notifications
        self.broker = None  # broker instance
        self.datas = list()  # datas that have registered over start

        self._orders = collections.OrderedDict()  # map order.ref to oid
        self._ordersrev = collections.OrderedDict()  # map oid to order.ref
        self._transpend = collections.defaultdict(collections.deque)

        _init_kabusapi_client(self.p.token, self.p.headers)
        
        self._cash = 0.0
        self._value = 0.0
        self._evt_acct = threading.Event()

    def start(self, data=None, broker=None):
        # Datas require some processing to kickstart data reception
        if data is None and broker is None:
            self.cash = None
            return

        if data is not None:
            self._env = data._env
            # For datas simulate a queue with None to kickstart co
            self.datas.append(data)

            if self.broker is not None:
                self.broker.data_started(data)

        elif broker is not None:
            self.broker = broker
            self.streaming_events()
            self.broker_threads()

    def stop(self):
        # signal end of thread
        if self.broker is not None:
            self.q_ordercreate.put(None)
            self.q_orderclose.put(None)
            self.q_account.put(None)

    def put_notification(self, msg, *args, **kwargs):
        self.notifs.append((msg, args, kwargs))

    def get_notifications(self):
        '''Return the pending "store" notifications'''
        self.notifs.append(None)  # put a mark / threads could still append
        return [x for x in iter(self.notifs.popleft, None)]

    # Oanda supported granularities
    # _GRANULARITIES = {
    #     (bt.TimeFrame.Seconds, 5): 'S5',
    #     (bt.TimeFrame.Seconds, 10): 'S10',
    #     (bt.TimeFrame.Seconds, 15): 'S15',
    #     (bt.TimeFrame.Seconds, 30): 'S30',
    #     (bt.TimeFrame.Minutes, 1): 'M1',
    #     (bt.TimeFrame.Minutes, 2): 'M3',
    #     (bt.TimeFrame.Minutes, 3): 'M3',
    #     (bt.TimeFrame.Minutes, 4): 'M4',
    #     (bt.TimeFrame.Minutes, 5): 'M5',
    #     (bt.TimeFrame.Minutes, 10): 'M5',
    #     (bt.TimeFrame.Minutes, 15): 'M5',
    #     (bt.TimeFrame.Minutes, 30): 'M5',
    #     (bt.TimeFrame.Minutes, 60): 'H1',
    #     (bt.TimeFrame.Minutes, 120): 'H2',
    #     (bt.TimeFrame.Minutes, 180): 'H3',
    #     (bt.TimeFrame.Minutes, 240): 'H4',
    #     (bt.TimeFrame.Minutes, 360): 'H6',
    #     (bt.TimeFrame.Minutes, 480): 'H8',
    #     (bt.TimeFrame.Days, 1): 'D',
    #     (bt.TimeFrame.Weeks, 1): 'W',
    #     (bt.TimeFrame.Months, 1): 'M',
    # }

    def get_positions(self):
        positions = self.kapi.positions()
        return positions

    #def get_granularity(self, timeframe, compression):
    #    return self._GRANULARITIES.get((timeframe, compression), None)

    # def get_instrument(self, dataname):
    #     try:
    #         insts = self.oapi.get_instruments(self.p.account_tmout,  # FIXME: oapi
    #                                           instruments=dataname)
    #     except (oandapy.OandaError, OandaRequestError,):
    #         return None
# 
    #     i = insts.get('instruments', [{}])
    #     return i[0] or None

    def streaming_events(self, tmout=None):
        q = queue.Queue()
        kwargs = {'q': q, 'tmout': tmout}

        t = threading.Thread(target=self._streaming_listener, kwargs=kwargs)
        t.daemon = True
        t.start()

        # t = threading.Thread(target=self._t_streaming_events, kwargs=kwargs) # FIXME: _t_streaming_events
        # t.daemon = True
        # t.start()
        return q

    # FIXME: @self.kapi.websocket
    def _streaming_listener(msg):
        '''
        Ref: https://github.com/shirasublue/python-kabusapi/blob/master/sample/push_sample.py
        '''
        # WIP
        pass
    #def _t_streaming_listener(self, q, tmout=None):
    #    while True:
    #        trans = q.get()
    #        self._transaction(trans)

    # FIXME: Streamer
    # def _t_streaming_events(self, q, tmout=None):
    #     if tmout is not None:
    #         _time.sleep(tmout)
# 
    #     # FIXME: oandapy.Streamer
    #     # streamer = Streamer(q,
    #     #                     environment=self._oenv,
    #     #                     access_token=self.p.token,
    #     #                     headers={'X-Accept-Datetime-Format': 'UNIX'})
# # 
    #     # streamer.events(ignore_heartbeat=False)

    def candles(self, dataname, dtbegin, dtend, timeframe, compression,
                candleFormat, includeFirst):

        kwargs = locals().copy()
        kwargs.pop('self')
        kwargs['q'] = q = queue.Queue()
        t = threading.Thread(target=self._t_candles, kwargs=kwargs) # FIXME: _t_candles
        t.daemon = True
        t.start()
        return q

    def _t_candles(self, dataname, dtbegin, dtend, timeframe, compression,
                   candleFormat, includeFirst, q):

        # FIXME: granularity = self.get_granularity(timeframe, compression)
        if granularity is None:
            e = OandaTimeFrameError()
            q.put(e.error_response)
            return

        dtkwargs = {}
        if dtbegin is not None:
            dtkwargs['start'] = int((dtbegin - self._DTEPOCH).total_seconds())  # FIXME: _DTEPOCH

        if dtend is not None:
            dtkwargs['end'] = int((dtend - self._DTEPOCH).total_seconds())  # FIXME: _DTEPOCH

        try:
            pass
            # FIXME: granularity
            # response = self.oapi.get_history(instrument=dataname,
            #                                  granularity=granularity,
            #                                  candleFormat=candleFormat,
            #                                  **dtkwargs)

        except oandapy.OandaError as e:
            q.put(e.error_response)
            q.put(None)
            return

        # FIXME
        for candle in response.get('candles', []):
            q.put(candle)

        q.put({})  # end of transmission

    def streaming_prices(self, dataname, tmout=None):
        q = queue.Queue()
        kwargs = {'q': q, 'dataname': dataname, 'tmout': tmout}
        t = threading.Thread(target=self._t_streaming_prices, kwargs=kwargs) # FIXME: _t_streaming_prices
        t.daemon = True
        t.start()
        return q

    # FIXME: Streamer
    def _t_streaming_prices(self, dataname, q, tmout):
        if tmout is not None:
            _time.sleep(tmout)

        # FIXME: Streamer
        # FIXME streamer = Streamer(q, environment=self._oenv,
        # FIXME                     access_token=self.p.token,
        # FIXME                     headers={'X-Accept-Datetime-Format': 'UNIX'})

        # FIXME streamer.rates(self.p.account, instruments=dataname)

    def get_cash(self):
        return self._cash

    def get_value(self):
        return self._value

    _ORDEREXECS = {
        bt.Order.Market: 'market',
        bt.Order.Limit: 'limit',
        bt.Order.Stop: 'stop',
        bt.Order.StopLimit: 'stop',
    }

    def broker_threads(self):
        self.q_account = queue.Queue()
        self.q_account.put(True)  # force an immediate update
        t = threading.Thread(target=self._t_account)
        t.daemon = True
        t.start()

        self.q_ordercreate = queue.Queue()
        t = threading.Thread(target=self._t_order_create)
        t.daemon = True
        t.start()

        self.q_orderclose = queue.Queue()
        t = threading.Thread(target=self._t_order_cancel)
        t.daemon = True
        t.start()

        # Wait once for the values to be set
        self._evt_acct.wait(self.p.account_tmout)

    def _t_account(self):
        while True:
            try:
                msg = self.q_account.get(timeout=self.p.account_tmout)
                if msg is None:
                    break  # end of thread
            except queue.Empty:  # tmout -> time to refresh
                pass

            try:
                accinfo = self.oapi.get_account(self.p.account)
            except Exception as e:
                self.put_notification(e)
                continue

            try:
                self._cash = accinfo['marginAvail']
                self._value = accinfo['balance']
            except KeyError:
                pass

            self._evt_acct.set()

    def order_create(self, order: bt.Order, stopside=None, takeside=None, **kwargs):
        okwargs = dict()
        okwargs['Symbol'] = order.data._dataname
        okwargs['Qty'] = abs(order.created.size)
        okwargs['Side'] = '2' if order.isbuy() else '1'
        okwargs['FrontOrderType'] = self._ORDEREXECS[order.exectype]
        if order.exectype != bt.Order.Market:
            okwargs['Price'] = order.created.price
            if order.valid is None:
                # maximum is 3 weeks later
                # https://kabu.com/rule/stock_trading.html#:~:text=%E3%81%94%E6%B3%A8%E6%96%87%E3%81%AE%E6%9C%89%E5%8A%B9%E6%9C%9F%E9%99%90,%E3%81%99%E3%82%8B%E3%81%93%E3%81%A8%E3%82%82%E5%8F%AF%E8%83%BD%E3%81%A7%E3%81%99%E3%80%82
                okwargs['ExpireDay'] = 0 # today
            else:
                valid = order.data.num2date(order.valid)
                okwargs['ExpireDay'] = int(valid.strftime('%Y%m%d'))

        # if order.exectype == bt.Order.StopLimit:
        #     okwargs['lowerBound'] = order.created.pricelimit
        #     okwargs['upperBound'] = order.created.pricelimit

        # if order.exectype == bt.Order.StopTrail:
        #     okwargs['trailingStop'] = order.trailamount

        # if stopside is not None:
        #     okwargs['stopLoss'] = stopside.price

        # if takeside is not None:
        #     okwargs['takeProfit'] = takeside.price

        okwargs.update(**kwargs)  # anything from the user

        self.q_ordercreate.put((order.ref, okwargs,))
        return order

    _OIDSINGLE = ['orderOpened', 'tradeOpened', 'tradeReduced']
    _OIDMULTIPLE = ['tradesClosed']

    def _t_order_create(self):
        while True:
            msg = self.q_ordercreate.get()
            if msg is None:
                break

            oref, okwargs = msg
            try:
                # https://github.com/shirasublue/python-kabusapi/blob/master/kabusapi/orders.py
                # https://github.com/shirasublue/python-kabusapi/blob/7e7a5ac232e037c651b5447b408d8b0b6727c9b0/sample/sample.py#L17-L35
                o = self.oapi.sendorder(**okwargs)
            except Exception as e:
                self.put_notification(e)
                self.broker._reject(oref)
                return

            # Ids are delivered in different fields and all must be fetched to
            # match them (as executions) to the order generated here
            oids = list()
            # for oidfield in self._OIDSINGLE:
            #     if oidfield in o and 'id' in o[oidfield]:
            #         oids.append(o[oidfield]['id'])
            oids.append(o['OrderId'])

            # for oidfield in self._OIDMULTIPLE:
            #     if oidfield in o:
            #         for suboidfield in o[oidfield]:
            #             oids.append(suboidfield['id'])

            if not oids:
                self.broker._reject(oref)
                return

            self._orders[oref] = oids[0]
            self.broker._submit(oref)
            if okwargs['FrontOrderType'] == 'market':
                self.broker._accept(oref)  # taken immediately

            for oid in oids:
                self._ordersrev[oid] = oref  # maps ids to backtrader order

                # An transaction may have happened and was stored
                tpending = self._transpend[oid]
                tpending.append(None)  # eom marker
                while True:
                    trans = tpending.popleft()
                    if trans is None:
                        break
                    self._process_transaction(oid, trans)

    def order_cancel(self, order):
        self.q_orderclose.put(order.ref)
        return order

    def _t_order_cancel(self):
        while True:
            oref = self.q_orderclose.get()
            if oref is None:
                break

            oid = self._orders.get(oref, None)
            if oid is None:
                continue  # the order is no longer there
            try:
                o = self.oapi.close_order(self.p.account, oid)
            except Exception as e:
                continue  # not cancelled - FIXME: notify

            self.broker._cancel(oref)

    _X_ORDER_CREATE = ('STOP_ORDER_CREATE',
                       'LIMIT_ORDER_CREATE', 'MARKET_IF_TOUCHED_ORDER_CREATE',)

    def _transaction(self, trans):
        '''
        ストリームイベントを拾って、ハンドルする。
        Invoked from Streaming Events. May actually receive an event for an
        oid which has not yet been returned after creating an order. Hence
        store if not yet seen, else forward to processer
        '''
        ttype = trans['type']
        if ttype == 'MARKET_ORDER_CREATE':
            try:
                oid = trans['tradeReduced']['id']
            except KeyError:
                try:
                    oid = trans['tradeOpened']['id']
                except KeyError:
                    return  # cannot do anything else

        elif ttype in self._X_ORDER_CREATE:
            oid = trans['id']
        elif ttype == 'ORDER_FILLED':
            oid = trans['orderId']

        elif ttype == 'ORDER_CANCEL':
            oid = trans['orderId']

        elif ttype == 'TRADE_CLOSE':
            oid = trans['id']
            pid = trans['tradeId']
            if pid in self._orders and False:  # Know nothing about trade
                return  # can do nothing

            # Skip above - at the moment do nothing
            # Received directly from an event in the WebGUI for example which
            # closes an existing position related to order with id -> pid
            # COULD BE DONE: Generate a fake counter order to gracefully
            # close the existing position
            msg = ('Received TRADE_CLOSE for unknown order, possibly generated'
                   ' over a different client or GUI')
            self.put_notification(msg, trans)
            return

        else:  # Go aways gracefully
            try:
                oid = trans['id']
            except KeyError:
                oid = 'None'

            msg = 'Received {} with oid {}. Unknown situation'
            msg = msg.format(ttype, oid)
            self.put_notification(msg, trans)
            return

        try:
            oref = self._ordersrev[oid]
            self._process_transaction(oid, trans)
        except KeyError:  # not yet seen, keep as pending
            self._transpend[oid].append(trans)

    _X_ORDER_FILLED = ('MARKET_ORDER_CREATE',
                       'ORDER_FILLED', 'TAKE_PROFIT_FILLED',
                       'STOP_LOSS_FILLED', 'TRAILING_STOP_FILLED',)

    def _process_transaction(self, oid, trans):
        try:
            oref = self._ordersrev.pop(oid)
        except KeyError:
            return

        ttype = trans['type']

        if ttype in self._X_ORDER_FILLED:
            size = trans['units']
            if trans['side'] == 'sell':
                size = -size
            price = trans['price']
            self.broker._fill(oref, size, price, ttype=ttype)

        elif ttype in self._X_ORDER_CREATE:
            self.broker._accept(oref)
            self._ordersrev[oid] = oref

        elif ttype in 'ORDER_CANCEL':
            reason = trans['reason']
            if reason == 'ORDER_FILLED':
                pass  # individual execs have done the job
            elif reason == 'TIME_IN_FORCE_EXPIRED':
                self.broker._expire(oref)
            elif reason == 'CLIENT_REQUEST':
                self.broker._cancel(oref)
            else:  # default action ... if nothing else
                self.broker._reject(oref)


# %%: Test
if __name__ == '__main__':
    from datetime import datetime
    import os
    from logging import DEBUG
    from kabu_s_handler import KabuSHandler
    from kabu_s_data import KabuSData
    from kabu_plus_jp_csv_data import KabuPlusJPCSVData
    
    host = os.environ.get('KABU_S_HOST')
    password = os.environ.get('KABU_S_PASSWORD')
    port = os.environ.get('KABU_S_PORT', 8081)
    headers = {'x-mock-response-code': '200'}
    store = KabuSAPIStore(password=password, host=host, port=port,
    headers=headers, token=os.environ.get('POSTMAN_API_KEY'))
    import pprint; pp = pprint.PrettyPrinter()

    def get_data():
        if not 'handler' in globals():
            handler = KabuSHandler(DEBUG)
        KabuSAPIStore.DataCls = KabuPlusJPCSVData
        data = KabuSAPIStore.getdata(
                dataname='japan-stock-prices_2021_7974.csv',
                compression=1,
                backfill=False,
                fromdate=datetime(2018, 1, 1),
                todate=datetime(2019, 1, 1),
                qcheck=0.5,
                timeframe=bt.TimeFrame.Minutes,
                backfill_start=False,
                historical=True,
                handler = handler)
        pp.pprint(data)
        return data
    get_data()

    def get_positions():
        print('get_positions()')
        pp.pprint(store.get_positions())
    get_positions()

    def order_buy():
        order = bt.BuyOrder(
            size=100,
            price=1234
        )
        store.order_create(order)
    order_buy()


# %%




