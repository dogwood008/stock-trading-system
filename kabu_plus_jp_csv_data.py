# -*- coding: utf-8 -*-

#############################################################
#    Copyright (C) 2020 dogwood008 (original author: Daniel Rodriguez; https://github.com/mementum/backtraders)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#############################################################

import csv
import io
import pytz
import re
from datetime import date, datetime
from backtrader.utils import date2num
from typing import Any
import backtrader as bt

class KabuPlusJPCSVData(bt.feeds.YahooFinanceCSVData):
    '''
    Parses pre-downloaded KABU+ CSV Data Feeds (or locally generated if they
    comply to the Yahoo formatｇ)
    Specific parameters:
      - ``dataname``: The filename to parse or a file-like object
      - ``reverse`` (default: ``True``)
        It is assumed that locally stored files have already been reversed
        during the download process
      - ``round`` (default: ``True``)
        Whether to round the values to a specific number of decimals after
        having adjusted the close
      - ``roundvolume`` (default: ``0``)
        Round the resulting volume to the given number of decimals after having
        adjusted it
      - ``decimals`` (default: ``2``)
        Number of decimals to round to
      - ``swapcloses`` (default: ``False``)
        [2018-11-16] It would seem that the order of *close* and *adjusted
        close* is now fixed. The parameter is retained, in case the need to
        swap the columns again arose.
    '''
    DATE = 'date'
    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'
    CLOSE = 'close'
    VOLUME = 'volume'
    ADJUSTED_CLOSE = 'adjusted_close'
    
    params = (
        ('reverse', True),
        ('dataname', None),
        ('round', True),
        ('decimals', 2),
        ('roundvolume', False),
        ('swapcloses', False),
        ('headers', True),
        ('header_names', {  # CSVのカラム名と内部的なキーを変換する辞書
            DATE: '日付',  # FIXME
            OPEN: '始値',
            HIGH: '高値',
            LOW: '安値',
            CLOSE: '株価',
            VOLUME: '出来高',
            ADJUSTED_CLOSE: 'adj_close',
        }),
        ('tz', pytz.timezone('Asia/Tokyo')),
        ('encoding', 'shift_jis'),
        ('quotechar', '"'),
        ('delimiter', ','),
        ('newline', '\r\n'),
    )

    def _fetch_value(self, values: dict, column_name: str) -> Any:
        '''
        パラメタで指定された変換辞書を使用して、
        CSVで定義されたカラム名に沿って値を取得する。
        '''
        index = self._column_index(self.p.header_names[column_name])
        return values[index]

        
    def _column_index(self, column_name: str) -> int:
        '''
        与えたカラム名に対するインデックス番号を返す。
        見つからなければ ValueError を投げる。
        '''
        return self._csv_headers.index(column_name)

    # copied from https://github.com/mementum/backtrader/blob/0426c777b0abdfafbb0988f5c31347553256a2de/backtrader/feed.py#L666-L679
    def start(self):
        super(bt.feed.CSVDataBase, self).start()

        if self.f is None:
            if hasattr(self.p.dataname, 'readline'):
                self.f = self.p.dataname
            else:
                # Let an exception propagate to let the caller know
                self.f = io.open(self.p.dataname, 'r',
                    encoding=self.p.encoding,
                    newline=self.p.newline)
                # https://docs.python.org/ja/3/library/csv.html
                # csvfile がファイルオブジェクトの場合、 newline='' として開くべきです。

        if self.p.headers and self.p.header_names:
            line = self.f.readline()
            # CSVとしての読み込みがうまくいかないので、手動でパースする
            # _csv_reader = csv.reader(line,
            #     delimiter=self.p.delimiter,
            #     quotechar=self.p.quotechar,
            #     quoting=csv.QUOTE_ALL,
            #     skipinitialspace=True)
            headers = re.sub(r'["\r\n]', '', line).split(',')
            self._csv_headers = headers

        self.separator = self.p.separator


    def _loadline(self, linetokens):
        while True:
            nullseen = False
            for tok in linetokens[1:]:
                if tok == 'null':
                    nullseen = True
                    linetokens = self._getnextline()  # refetch tokens
                    if not linetokens:
                        return False  # cannot fetch, go away

                    # out of for to carry on wiwth while True logic
                    break

            if not nullseen:
                break  # can proceed

        dttxt = self._fetch_value(linetokens, self.DATE)
        import pdb; pdb.set_trace() 
        dt = date(int(dttxt[0:4]), int(dttxt[5:7]), int(dttxt[8:10]))
        dtnum = date2num(datetime.combine(dt, self.p.sessionend))
        #dtnum = date2num(datetime.combine(dt, self.p.sessionend), tz=pytz.timezone('Asia/Tokyo'))

        self.lines.datetime[0] = dtnum
        o = float(self._fetch_value(linetokens, self.OPEN))
        h = float(self._fetch_value(linetokens, self.HIGH))
        l = float(self._fetch_value(linetokens, self.LOW))
        rawc = float(self._fetch_value(linetokens, self.CLOSE))
        self.lines.openinterest[0] = 0.0

        adjustedclose = float(self._fetch_value(linetokens, self.ADJUSTED_CLOSE))
        v = float(self._fetch_value(linetokens, self.VOLUME))

        if self.p.swapcloses:  # swap closing prices if requested
            rawc, adjustedclose = adjustedclose, rawc

        adjfactor = rawc / adjustedclose

        o /= adjfactor
        h /= adjfactor
        l /= adjfactor
        v *= adjfactor

        if self.p.round:
            decimals = self.p.decimals
            o = round(o, decimals)
            h = round(h, decimals)
            l = round(l, decimals)
            rawc = round(rawc, decimals)

        v = round(v, self.p.roundvolume)

        self.lines.open[0] = o
        self.lines.high[0] = h
        self.lines.low[0] = l
        self.lines.close[0] = adjustedclose
        self.lines.volume[0] = v

        return True
