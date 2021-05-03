
import re
import dill
import jpbizday
from jpbizday.jpbizday import bizdays
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime, timezone, timedelta
import argparse

class AddAdjClose:
    JST: timezone = timezone(timedelta(hours=+9), 'JST')

    def get_adj_rate(self, paths_to_html: List[str]) -> pd.DataFrame:
        '''
        与えたHTMLファイルから、終値調整比を作成して、DFで返す。
        得られる適用日の次営業日から、調整比が有効になるので、その点注意。

        Parameters
        ---------------------
        path_to_html: List[str]
            相対パスor絶対パス

        Returns
        ---------------------
        dataframe: pd.DataFrame
        '''

        def _convert_to_ratio(nl: str) -> float: 
            before, after = re.split('[→：]', nl.replace('株', ''))
            return float(after) / float(before)

        def _html2df(path_to_html: str) -> pd.DataFrame:
            html = open(path_to_html).read()

            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', {'class': 'tbl01'})
            rows = table.findAll('tr')
            csv = [
                [cell.get_text() for cell in row.findAll(['td', 'th'])]
                for row in rows
            ]
            df = pd.DataFrame(csv, columns=csv.pop(0)) \
                    .rename(columns={'銘柄コード': 'code',  # 扱いやすいように半角にしておく
                                    '銘柄名': 'name',
                                    '併合比率': 'rate', '割当比率': 'rate',
                                    '権利付最終日': 'from'})
            return df

        def _adj_rates(df_in_desc: pd.DataFrame) -> list:
            '''
            Parameters
            ----------------------
            df_in_desc: pd.DataFrame
                日時降順でソートし与えること。
            '''
            adj_rates_in_each_codes: dict = {}
            def calc_adj_rates(code: str, rate: float):
                adj_rates_in_each_codes[code] = adj_rates_in_each_codes.get(code, 1.0) / rate
                return adj_rates_in_each_codes[code]
            return [calc_adj_rates(code, rate)
                for code, rate in df_in_desc[['code', 'rate']].values]

        def _reverse(df: pd.DataFrame) -> pd.DataFrame:
            # https://stackoverflow.com/a/20444256
            return df.iloc[::-1]

        dfs = pd.concat(_html2df(path_to_html) \
                for path_to_html in paths_to_html) \
                .sort_values(['code', 'from'], ascending=False)
        dfs['rate'] = dfs['rate'].apply(_convert_to_ratio)
        dfs['adj_rate'] = _adj_rates(dfs)
        dfs['adj_rate'] = dfs['adj_rate'].astype(np.float64)
        dfs['date'] = dfs['from'].apply(self.three_separated_digits_to_date) #lambda x: date(*map(lambda y: int(y), x.split('/'))))
        return _reverse(dfs)[['code', 'name', 'date', 'rate', 'adj_rate']]

    def save_as_dill(self, df: pd.DataFrame,
            path_to_dill: str='adj_rates.dill'):
        dill.dump(df, open(path_to_dill, 'wb'))

    def load_from_dill(self,
            path_to_dill: str='adj_rates.dill') -> pd.DataFrame:
        return dill.load(open(path_to_dill, 'rb'))

    def three_separated_digits_to_date(self, date_str: str) -> datetime:
        '''
        YYYY-MM-DD や YYYY/MM/DD や 'YYYY MM DD' のstrをパースして、datetimeで返す。
        '''
        ymd = map(lambda x: int(x), re.split('[-/ ]', date_str)[0:3])
        return datetime(*ymd, 15, 0, 0, tzinfo=self.JST)

    def hist_data(self, filepath: str) -> pd.DataFrame:
        '''
        銘柄コード、年を指定して、CSVを読み込み、DFを返す。
        '''
        csv = pd.read_csv(filepath, encoding='shift_jis')
        columns = {'SC': 'code', '名称': 'name', \
                        '市場': 'market', '業種': 'industry', \
                        '日時': 'date', '株価': 'close', '始値': 'open', \
                        '高値': 'high', '安値': 'low', '出来高': 'volumes'}
        csv = csv.rename(columns=columns)
        csv['date'] = csv['date'].apply(self.three_separated_digits_to_date)
        return csv.loc[:, columns.values()]

    def _bizdays(self, year: int) -> pd.DataFrame:
        biz_days = jpbizday.year_bizdays(year)
        biz_dts = map(lambda x: \
            datetime(x.year, x.month, x.day, 15, 0, 0, tzinfo=self.JST), biz_days)
        bizdays_df = pd.DataFrame({'date': biz_dts}).set_index('date')
        return bizdays_df

    def hist_data_with_adj_close(self, hist_data: pd.DataFrame, \
            code: str, year: str, adj_rate_df: pd.DataFrame) -> pd.DataFrame:
        '''
        銘柄コード、年、終値調整用比のDFから、調整後終値付きのDFを返す。
        '''
        adj_rate_for_current_stock: pd.DataFrame = adj_rate_df[adj_rate_df['code'] == code]
        joined = self._bizdays(year).merge(adj_rate_for_current_stock, \
                                    on='date', how='left') \
                            .set_index('date').shift() \
                            .fillna(method='ffill').fillna(1.0)
        adj = joined.loc[:, ['adj_rate']]
        #hist = hist_data(input_filepath)
        hist = hist_data.merge(adj, on='date', how='left')
        latest_rate = hist.iloc[-1]['adj_rate']
        hist['adj_close'] = hist['close'] * (latest_rate / hist['adj_rate'])
        hist = hist.set_index('date')
        return hist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='KABU+ converter')

    parser.add_argument('--input', '-i', default=None, type=str,
                        required=True, action='store',
                        help='input file path')

    parser.add_argument('--output', '-o', default=None, type=str,
                        required=True, action='store',
                        help='output file path')

    parser.add_argument('--year', '-y', default=None, type=int,
                        required=True, action='store',
                        help='the year of file path')

    parser.add_argument('--codes', '-c', default=None, type=str,
                        required=True, action='store',
                        help='the stock codes of file (comma separated)')

    parser.add_argument('--dill-input', default=None, type=str,
                        required=False, action='store',
                        help='dill input file path')

    parser.add_argument('--dill-output', default=None, type=str,
                        required=False, action='store',
                        help='dill output file path')

    parser.add_argument('--heigou-input', default=None, type=str,
                        required=False, action='store',
                        help='heigou html input file path')

    parser.add_argument('--bunkatsu-input', default=None, type=str,
                        required=False, action='store',
                        help='bunkatsu html input file path')

    return parser.parse_args()

def main():
    args = parse_args()
    aac = AddAdjClose()
    if args.dill_input:
        adj_rate_df = aac.load_from_dill(args.dill_input)
    else:
        adj_rate_df = aac.get_adj_rate((args.heigou_input, args.bunkatsu_input))
    if args.dill_output:
        aac.save_as_dill(adj_rate_df, args.dill_output)

    year = args.year
    codes = args.codes.split(',')
    hist_data_df: pd.DataFrame = aac.hist_data(args.input)
    [aac.hist_data_with_adj_close(hist_data_df, code, year, adj_rate_df) \
            .to_csv(args.output % code) for code in codes]

if __name__ == '__main__':
    main()
