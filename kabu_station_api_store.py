#!/usr/bin/env python
# coding: utf-8

# ## Utilities

# In[1]:


def is_in_jupyter() -> bool:
    '''
    Determine wheather is the environment Jupyter Notebook
    https://blog.amedama.jp/entry/detect-jupyter-env
    '''
    if 'get_ipython' not in globals():
        # Python shell
        return False
    env_name = get_ipython().__class__.__name__
    if env_name == 'TerminalInteractiveShell':
        # IPython shell
        return False
    # Jupyter Notebook
    return True
print(is_in_jupyter())


# In[2]:


# https://recruit-tech.co.jp/blog/2018/10/16/jupyter_notebook_tips/
if is_in_jupyter():
    def set_stylesheet():
        from IPython.display import display, HTML
        css = get_ipython().getoutput('wget https://raw.githubusercontent.com/lapis-zero09/jupyter_notebook_tips/master/css/jupyter_notebook/monokai.css -q -O -')
        css = "\n".join(css)
        display(HTML('<style type="text/css">%s</style>'%css))
    set_stylesheet()


# ## Logger

# In[41]:


# ログ用
from logging import Logger, getLogger, StreamHandler, Formatter, DEBUG, INFO, WARN
from pprint import PrettyPrinter
class KabuSLogger:
    # VERBOSE = DEBUG / 2
    def __init__(self, loglevel: int=INFO):
        self._logger = getLogger(__name__)
        self._handler = StreamHandler()
        self._handler.setLevel(loglevel)
        self._logger.setLevel(DEBUG)
        self._logger.addHandler(self.handler)
        self._logger.propagate = False
        self._handler.setFormatter(
                Formatter('[%(levelname)s] %(message)s'))
    @property
    def logger(self) -> Logger:
        return self._logger
    
    @property
    def handler(self) -> StreamHandler:
        return self._handler
    
    # def verbose(self, msg, *args, **kwargs):
    #     self.log(self.VERBOSE, msg, args, kwargs)
        
    def debug(self, msg, **kwargs):
        self.log(DEBUG, msg, **kwargs)
        
    def info(self, msg, **kwargs):
        self.log(INFO, msg, **kwargs)
        
    def warn(self, msg, **kwargs):
        self.log(WARN, msg, **kwargs)
        
    def log(self, level, msg, **kwargs):
        if kwargs:
            self._logger.log(level, msg, **kwargs)
        else:
            self._logger.log(level, msg)
    
logger = KabuSLogger(DEBUG)
logger.debug('test')
logger.info('test')


# ## Main

# In[ ]:


#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2020 Daniel Rodriguez
# Copyright (C) 2021 dogwood008 (modified)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
from datetime import datetime, timedelta
import time as _time
import json
import threading

# import oandapy
# import requests  # oandapy depdendency

import backtrader as bt
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import queue, with_metaclass
from backtrader.utils import AutoDict

import kabusapi
kabusapi.Context
############################################
## ここまで動作確認済み


# ## for reference

# In[ ]:


# Extend the exceptions to support extra cases
# '''
# class OandaRequestError(oandapy.OandaError):
#     def __init__(self):
#         er = dict(code=599, message='Request Error', description='')
#         super(self.__class__, self).__init__(er)
# 
# 
# class OandaStreamError(oandapy.OandaError):
#     def __init__(self, content=''):
#         er = dict(code=598, message='Failed Streaming', description=content)
#         super(self.__class__, self).__init__(er)
# 
# 
# class OandaTimeFrameError(oandapy.OandaError):
#     def __init__(self, content):
#         er = dict(code=597, message='Not supported TimeFrame', description='')
#         super(self.__class__, self).__init__(er)
# 
# 
# class OandaNetworkError(oandapy.OandaError):
#     def __init__(self):
#         er = dict(code=596, message='Network Error', description='')
#         super(self.__class__, self).__init__(er)
# '''

# class API(oandapy.API):
#     def request(self, endpoint, method='GET', params=None):
#         # Overriden to make something sensible out of a
#         # request.RequestException rather than simply issuing a print(str(e))
#         url = '%s/%s' % (self.api_url, endpoint)
# 
#         method = method.lower()
#         params = params or {}
# 
#         func = getattr(self.client, method)
# 
#         request_args = {}
#         if method == 'get':
#             request_args['params'] = params
#         else:
#             request_args['data'] = params
# 
#         # Added the try block
#         try:
#             response = func(url, **request_args)
#         except requests.RequestException as e:
#             return OandaRequestError().error_response
# 
#         content = response.content.decode('utf-8')
#         content = json.loads(content)
# 
#         # error message
#         if response.status_code >= 400:
#             # changed from raise to return
#             return oandapy.OandaError(content).error_response
# 
#         return content


# ## for reference

# In[ ]:


#FIXME
# class Streamer(oandapy.Streamer):
#     def __init__(self, q, headers=None, *args, **kwargs):
#         # Override to provide headers, which is in the standard API interface
#         super(Streamer, self).__init__(*args, **kwargs)
# 
#         if headers:
#             self.client.headers.update(headers)
# 
#         self.q = q
# 
#     def run(self, endpoint, params=None):
#         # Override to better manage exceptions.
#         # Kept as much as possible close to the original
#         self.connected = True
# 
#         params = params or {}
# 
#         ignore_heartbeat = None
#         if 'ignore_heartbeat' in params:
#             ignore_heartbeat = params['ignore_heartbeat']
# 
#         request_args = {}
#         request_args['params'] = params
# 
#         url = '%s/%s' % (self.api_url, endpoint)
# 
#         while self.connected:
#             # Added exception control here
#             try:
#                 response = self.client.get(url, **request_args)
#             except requests.RequestException as e:
#                 self.q.put(OandaRequestError().error_response)
#                 break
# 
#             if response.status_code != 200:
#                 self.on_error(response.content)
#                 break  # added break here
# 
#             # Changed chunk_size 90 -> None
#             try:
#                 for line in response.iter_lines(chunk_size=None):
#                     if not self.connected:
#                         break
# 
#                     if line:
#                         data = json.loads(line.decode('utf-8'))
#                         if not (ignore_heartbeat and 'heartbeat' in data):
#                             self.on_success(data)
# 
#             except:  # socket.error has been seen
#                 self.q.put(OandaStreamError().error_response)
#                 break
# 
#     def on_success(self, data):
#         if 'tick' in data:
#             self.q.put(data['tick'])
#         elif 'transaction' in data:
#             self.q.put(data['transaction'])
# 
#     def on_error(self, data):
#         self.disconnect()
#         self.q.put(OandaStreamError(data).error_response)


# ## Main

# ## KabuSAPIEnv

# In[ ]:


from enum import Enum
class KabuSAPIEnv(Enum):
    DEV = 'dev'
    PROD = 'prod'


# ## MetaSingleton

# In[ ]:


class MetaSingleton(MetaParams):
    '''Metaclass to make a metaclassed class a singleton'''
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton


# ## KabuSAPIStore

# In[ ]:


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
        ('url', 'localhost'),
        ('env', KabuSAPIEnv.DEV),
        ('port', None),
        ('password', None),
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

    def __init__(self):
        def _getport() -> int:
            if self.p.port:
                return port
            return 18081 if self.p.env == KabuSAPIEnv.DEV else 18080

        def _init_kabusapi_client() -> kabusapi.Context:
            url = self.p.url
            port = self.p.port or _getport()
            password = self.p.password
            token = kabusapi.Context(url, port, password).token
            self.kapi = kabusapi.Context(url, port, token=token)
            
        super(KabuSAPIStore, self).__init__()

        self.notifs = collections.deque()  # store notifications for cerebro

        self._env = None  # reference to cerebro for general notifications
        self.broker = None  # broker instance
        self.datas = list()  # datas that have registered over start

        self._orders = collections.OrderedDict()  # map order.ref to oid
        self._ordersrev = collections.OrderedDict()  # map oid to order.ref
        self._transpend = collections.defaultdict(collections.deque)

        _init_kabusapi_client()
        
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
        try:
            positions = self.kapi.positions()
        except (oandapy.OandaError, OandaRequestError,):
            # FIXME: Error handling
            return None

        poslist = positions.get('positions', [])
        return poslist

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
        # q = queue.Queue()
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

    def order_create(self, order, stopside=None, takeside=None, **kwargs):
        okwargs = dict()
        okwargs['instrument'] = order.data._dataname
        okwargs['units'] = abs(order.created.size)
        okwargs['side'] = 'buy' if order.isbuy() else 'sell'
        okwargs['type'] = self._ORDEREXECS[order.exectype]
        if order.exectype != bt.Order.Market:
            okwargs['price'] = order.created.price
            if order.valid is None:
                # 1 year and datetime.max fail ... 1 month works
                valid = datetime.utcnow() + timedelta(days=30)
            else:
                valid = order.data.num2date(order.valid)
                # To timestamp with seconds precision
            okwargs['expiry'] = int((valid - self._DTEPOCH).total_seconds()) # FIXME: _DTEPOCH

        if order.exectype == bt.Order.StopLimit:
            okwargs['lowerBound'] = order.created.pricelimit
            okwargs['upperBound'] = order.created.pricelimit

        if order.exectype == bt.Order.StopTrail:
            okwargs['trailingStop'] = order.trailamount

        if stopside is not None:
            okwargs['stopLoss'] = stopside.price

        if takeside is not None:
            okwargs['takeProfit'] = takeside.price

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
                o = self.oapi.create_order(self.p.account, **okwargs)
            except Exception as e:
                self.put_notification(e)
                self.broker._reject(oref)
                return

            # Ids are delivered in different fields and all must be fetched to
            # match them (as executions) to the order generated here
            oids = list()
            for oidfield in self._OIDSINGLE:
                if oidfield in o and 'id' in o[oidfield]:
                    oids.append(o[oidfield]['id'])

            for oidfield in self._OIDMULTIPLE:
                if oidfield in o:
                    for suboidfield in o[oidfield]:
                        oids.append(suboidfield['id'])

            if not oids:
                self.broker._reject(oref)
                return

            self._orders[oref] = oids[0]
            self.broker._submit(oref)
            if okwargs['type'] == 'market':
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


# ## KabuSAPICommInfo

# In[ ]:


# WIP

# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2020 Daniel Rodriguez
# Copyright (C) 2021 dogwood008 (modified)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
from copy import copy
from datetime import date, datetime, timedelta
import threading

from backtrader.feed import DataBase
from backtrader import (TimeFrame, num2date, date2num, BrokerBase,
                        Order, BuyOrder, SellOrder, OrderBase, OrderData)
from backtrader.utils.py3 import bytes, with_metaclass, MAXFLOAT
from backtrader.metabase import MetaParams
from backtrader.comminfo import CommInfoBase
from backtrader.position import Position
from backtrader.utils import AutoDict, AutoOrderedDict
from backtrader.comminfo import CommInfoBase


class OandaCommInfo(CommInfoBase):
    def getvaluesize(self, size, price):
        # In real life the margin approaches the price
        return abs(size) * price

    def getoperationcost(self, size, price):
        '''Returns the needed amount of cash an operation would cost'''
        # Same reasoning as above
        return abs(size) * price
KabuSCommInfo = OandaCommInfo
    


class MetaOandaBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaOandaBroker, cls).__init__(name, bases, dct)
        KabuSAPIStore.BrokerCls = cls
MetaKabuSBroker = MetaOandaBroker


# ## OandaBroker

# In[ ]:


class OandaBroker(with_metaclass(MetaOandaBroker, BrokerBase)):
    '''Broker implementation for Oanda.

    This class maps the orders/positions from Oanda to the
    internal API of ``backtrader``.

    Params:

      - ``use_positions`` (default:``True``): When connecting to the broker
        provider use the existing positions to kickstart the broker.

        Set to ``False`` during instantiation to disregard any existing
        position
    '''
    params = (
        ('use_positions', True),
        ('commission', OandaCommInfo(mult=1.0, stocklike=False)),
    )

    def __init__(self, **kwargs):
        super(OandaBroker, self).__init__()

        self.o = KabuSAPIStore(**kwargs)

        self.orders = collections.OrderedDict()  # orders by order id
        self.notifs = collections.deque()  # holds orders which are notified

        self.opending = collections.defaultdict(list)  # pending transmission
        self.brackets = dict()  # confirmed brackets

        self.startingcash = self.cash = 0.0
        self.startingvalue = self.value = 0.0
        self.positions = collections.defaultdict(Position)

    def start(self):
        super(OandaBroker, self).start()
        self.o.start(broker=self)
        self.startingcash = self.cash = cash = self.o.get_cash()
        self.startingvalue = self.value = self.o.get_value()

        if self.p.use_positions:
            for p in self.o.get_positions():
                print('position for instrument:', p['instrument'])
                is_sell = p['side'] == 'sell'
                size = p['units']
                if is_sell:
                    size = -size
                price = p['avgPrice']
                self.positions[p['instrument']] = Position(size, price)

    def data_started(self, data):
        pos = self.getposition(data)

        if pos.size < 0:
            order = SellOrder(data=data,
                              size=pos.size, price=pos.price,
                              exectype=Order.Market,
                              simulated=True)

            order.addcomminfo(self.getcommissioninfo(data))
            order.execute(0, pos.size, pos.price,
                          0, 0.0, 0.0,
                          pos.size, 0.0, 0.0,
                          0.0, 0.0,
                          pos.size, pos.price)

            order.completed()
            self.notify(order)

        elif pos.size > 0:
            order = BuyOrder(data=data,
                             size=pos.size, price=pos.price,
                             exectype=Order.Market,
                             simulated=True)

            order.addcomminfo(self.getcommissioninfo(data))
            order.execute(0, pos.size, pos.price,
                          0, 0.0, 0.0,
                          pos.size, 0.0, 0.0,
                          0.0, 0.0,
                          pos.size, pos.price)

            order.completed()
            self.notify(order)

    def stop(self):
        super(OandaBroker, self).stop()
        self.o.stop()

    def getcash(self):
        # This call cannot block if no answer is available from oanda
        self.cash = cash = self.o.get_cash()
        return cash

    def getvalue(self, datas=None):
        self.value = self.o.get_value()
        return self.value

    def getposition(self, data, clone=True):
        # return self.o.getposition(data._dataname, clone=clone)
        pos = self.positions[data._dataname]
        if clone:
            pos = pos.clone()

        return pos

    def orderstatus(self, order):
        o = self.orders[order.ref]
        return o.status

    def _submit(self, oref):
        order = self.orders[oref]
        order.submit(self)
        self.notify(order)
        for o in self._bracketnotif(order):
            o.submit(self)
            self.notify(o)

    def _reject(self, oref):
        order = self.orders[oref]
        order.reject(self)
        self.notify(order)
        self._bracketize(order, cancel=True)

    def _accept(self, oref):
        order = self.orders[oref]
        order.accept()
        self.notify(order)
        for o in self._bracketnotif(order):
            o.accept(self)
            self.notify(o)

    def _cancel(self, oref):
        order = self.orders[oref]
        order.cancel()
        self.notify(order)
        self._bracketize(order, cancel=True)

    def _expire(self, oref):
        order = self.orders[oref]
        order.expire()
        self.notify(order)
        self._bracketize(order, cancel=True)

    def _bracketnotif(self, order):
        pref = getattr(order.parent, 'ref', order.ref)  # parent ref or self
        br = self.brackets.get(pref, None)  # to avoid recursion
        return br[-2:] if br is not None else []

    def _bracketize(self, order, cancel=False):
        pref = getattr(order.parent, 'ref', order.ref)  # parent ref or self
        br = self.brackets.pop(pref, None)  # to avoid recursion
        if br is None:
            return

        if not cancel:
            if len(br) == 3:  # all 3 orders in place, parent was filled
                br = br[1:]  # discard index 0, parent
                for o in br:
                    o.activate()  # simulate activate for children
                self.brackets[pref] = br  # not done - reinsert children

            elif len(br) == 2:  # filling a children
                oidx = br.index(order)  # find index to filled (0 or 1)
                self._cancel(br[1 - oidx].ref)  # cancel remaining (1 - 0 -> 1)
        else:
            # Any cancellation cancel the others
            for o in br:
                if o.alive():
                    self._cancel(o.ref)

    def _fill(self, oref, size, price, ttype, **kwargs):
        order = self.orders[oref]

        if not order.alive():  # can be a bracket
            pref = getattr(order.parent, 'ref', order.ref)
            if pref not in self.brackets:
                msg = ('Order fill received for {}, with price {} and size {} '
                       'but order is no longer alive and is not a bracket. '
                       'Unknown situation')
                msg.format(order.ref, price, size)
                self.put_notification(msg, order, price, size)
                return

            # [main, stopside, takeside], neg idx to array are -3, -2, -1
            if ttype == 'STOP_LOSS_FILLED':
                order = self.brackets[pref][-2]
            elif ttype == 'TAKE_PROFIT_FILLED':
                order = self.brackets[pref][-1]
            else:
                msg = ('Order fill received for {}, with price {} and size {} '
                       'but order is no longer alive and is a bracket. '
                       'Unknown situation')
                msg.format(order.ref, price, size)
                self.put_notification(msg, order, price, size)
                return

        data = order.data
        pos = self.getposition(data, clone=False)
        psize, pprice, opened, closed = pos.update(size, price)

        comminfo = self.getcommissioninfo(data)

        closedvalue = closedcomm = 0.0
        openedvalue = openedcomm = 0.0
        margin = pnl = 0.0

        order.execute(data.datetime[0], size, price,
                      closed, closedvalue, closedcomm,
                      opened, openedvalue, openedcomm,
                      margin, pnl,
                      psize, pprice)

        if order.executed.remsize:
            order.partial()
            self.notify(order)
        else:
            order.completed()
            self.notify(order)
            self._bracketize(order)

    def _transmit(self, order):
        oref = order.ref
        pref = getattr(order.parent, 'ref', oref)  # parent ref or self

        if order.transmit:
            if oref != pref:  # children order
                # Put parent in orders dict, but add stopside and takeside
                # to order creation. Return the takeside order, to have 3s
                takeside = order  # alias for clarity
                parent, stopside = self.opending.pop(pref)
                for o in parent, stopside, takeside:
                    self.orders[o.ref] = o  # write them down

                self.brackets[pref] = [parent, stopside, takeside]
                self.o.order_create(parent, stopside, takeside)
                return takeside  # parent was already returned

            else:  # Parent order, which is not being transmitted
                self.orders[order.ref] = order
                return self.o.order_create(order)

        # Not transmitting
        self.opending[pref].append(order)
        return order

    def buy(self, owner, data,
            size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            parent=None, transmit=True,
            **kwargs):

        order = BuyOrder(owner=owner, data=data,
                         size=size, price=price, pricelimit=plimit,
                         exectype=exectype, valid=valid, tradeid=tradeid,
                         trailamount=trailamount, trailpercent=trailpercent,
                         parent=parent, transmit=transmit)

        order.addinfo(**kwargs)
        order.addcomminfo(self.getcommissioninfo(data))
        return self._transmit(order)

    def sell(self, owner, data,
             size, price=None, plimit=None,
             exectype=None, valid=None, tradeid=0, oco=None,
             trailamount=None, trailpercent=None,
             parent=None, transmit=True,
             **kwargs):

        order = SellOrder(owner=owner, data=data,
                          size=size, price=price, pricelimit=plimit,
                          exectype=exectype, valid=valid, tradeid=tradeid,
                          trailamount=trailamount, trailpercent=trailpercent,
                          parent=parent, transmit=transmit)

        order.addinfo(**kwargs)
        order.addcomminfo(self.getcommissioninfo(data))
        return self._transmit(order)

    def cancel(self, order):
        o = self.orders[order.ref]
        if order.status == Order.Cancelled:  # already cancelled
            return

        return self.o.order_cancel(order)

    def notify(self, order):
        self.notifs.append(order.clone())

    def get_notification(self):
        if not self.notifs:
            return None

        return self.notifs.popleft()

    def next(self):
        self.notifs.append(None)  # mark notification boundary


# ## KabuSBroker

# In[ ]:


KabuSBroker = OandaBroker


# In[ ]:


import pprint

from backtrader.feed import DataBase
class MetaOandaData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaOandaData, cls).__init__(name, bases, dct)

        # Register with the store
        KabuSAPIStore.DataCls = cls


class OandaData(with_metaclass(MetaOandaData, DataBase)): # FIXME
    def __init__(self, *args, **kwargs):
        pp = pprint.PrettyPrinter()
        pp.pprint(args)
        pp.pprint(kwargs)
        pp.pprint(f'{self} called.')


# ## Test

# In[ ]:


# https://community.backtrader.com/topic/1570/oanda-data-feed

class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])


# In[ ]:


import os
from datetime import datetime
if __name__ == '__main__':

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    password = os.environ.get('PASSWORD')
    # Create oandastore
    kabusapistore = KabuSAPIStore(password = password)
    kabusapistore.BrokerCls = KabuSBroker()
    kabusapistore.DataCls = OandaBroker()
    # instantiate data    
    data = kabusapistore.getdata(dataname='EUR_USD', 
                       compression=1,
                       backfill=False,
                       fromdate=datetime(2018, 1, 1),
                       todate=datetime(2019, 1, 1),
                       qcheck=0.5,
                       timeframe=bt.TimeFrame.Minutes,
                       backfill_start=False,
                       historical=False)


    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set cash of default broker
    cerebro.broker.setcash(10000.0)

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())


# In[ ]:





# In[ ]:




