# import akshare as ak
# import datetime
# import os
#
# index_pool = ['上证180ETF', '中证500ETF', '黄金ETF']
# codes = ["510180", "510590", "518880"]
#
# if __name__ == '__main__':
#     dt_now = datetime.datetime.now().strftime('%Y%m%d')
#     dt_before = '2017-01-01'
#
#     dir_path = 'D:\\PPrograms\\Python\\JoinQuant策略'
#     if not os.path.exists(dir_path):
#         os.makedirs(dir_path)
#
#     # 更新沪深300
#     data = ak.index_zh_a_hist(symbol='000300', period="daily",start_date=dt_before,end_date=dt_now)
#     data.to_csv(f'{dir_path}\沪深300.csv', header=True, index=False, encoding='gbk')
#     data.to_excel(f'{dir_path}\沪深300.xlsx', header=True, index=False)
#
#     # 更新etf池
#     for i, code in enumerate(codes):
#         data = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=dt_before, end_date=dt_now, adjust="")
#         data.to_csv(f'{dir_path}\\{index_pool[i]}.csv', header=True, index=False, encoding='gbk')


import requests
import re
import ast
import pandas as pd
import datetime
import os

dir_path = 'D:\\PPrograms\\Python\\JoinQuant策略'
if not os.path.exists(dir_path):
    os.makedirs(dir_path)

code_index = {
    "510180": '上证180ETF',
    "510590": '中证500ETF',
    "518880": '黄金ETF',
}

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
}
compiler = re.compile(r'fortune_hq\((.*?)\)')

def get_code_data(code, date):
    pre = pd.read_csv(f'{dir_path}\\{code_index[code]}.csv', header=0, encoding='gbk')

    url = f'https://hq.stock.sohu.com/cn/{code[-3:]}/cn_{code}-1.html'
    resp = requests.get(url, headers=headers).text
    data = ast.literal_eval(compiler.findall(resp)[0])

    ret = pd.Series(index=['日期','开盘','收盘','最高','最低','成交量','成交额','振幅','涨跌幅','涨跌额','换手率'])
    ret['日期'] = date
    ret['开盘'] = float(data['price_A2'][3])
    ret['收盘'] = float(data['price_A1'][2])
    ret['最高'] = float(data['price_A2'][5])
    ret['最低'] = float(data['price_A2'][7])
    ret['成交量'] = int(data['price_A2'][8])
    ret['成交额'] = int(data['price_A2'][12])*10000
    ret['振幅'] = round((ret['最高']-ret['最低'])/pre['收盘'].iloc[-1]*100,2)
    ret['涨跌幅'] = float(data['price_A1'][4][:-1])
    ret['涨跌额'] = float(data['price_A1'][3][1:])
    ret['换手率'] = float(data['price_A2'][6][:-1])
    ret.to_frame()

    pre = pre._append(ret,ignore_index=True)
    pre.to_csv(f'{dir_path}\\{code_index[code]}.csv', header=True, index=False, encoding='gbk')

    pass

def hs300_data(date):
    url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000300&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&klt=101&fqt=1&end=20500101&lmt=1'
    resp = requests.get(url, headers=headers).text
    data = ast.literal_eval(resp)['data']['klines'][0].split(',')
    pre = pd.read_csv(f'{dir_path}\沪深300.csv', header=0, encoding='gbk')

    ret = pd.Series(index=['日期','开盘','收盘','最高','最低','成交量','成交额','振幅','涨跌幅','涨跌额','换手率'])
    ret['日期'] = date
    ret['开盘'] = float(data[1])
    ret['收盘'] = float(data[2])
    ret['最高'] = float(data[3])
    ret['最低'] = float(data[4])
    ret['成交量'] = int(data[5])
    ret['成交额'] = int(float(data[6]))
    ret['振幅'] = float(data[7])
    ret['涨跌幅'] = float(data[8])
    ret['涨跌额'] = float(data[9])
    ret['换手率'] = float(data[10])
    ret.to_frame()
    pre = pre._append(ret,ignore_index=True)

    pre.to_csv(f'{dir_path}\沪深300.csv', header=True, index=False, encoding='gbk')
    pre.to_excel(f'{dir_path}\沪深300.xlsx', header=True, index=False)

    pass


if __name__ == '__main__':
    # 更新etf池
    date = datetime.datetime.now().strftime('%Y/%#m/%#d')
    for code in code_index:
        get_code_data(code, date)
    # 更新hs300
    hs300_data(date)