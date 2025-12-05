import sys
from pathlib import Path

# 获取当前脚本的绝对路径，并找到项目根目录
project_root = Path(__file__).parent.parent  # 根据实际情况调整层级
sys.path.append(str(project_root))  # 添加根目录到 Python 路径

import sys
import bisect
import numpy as np
import pandas as pd
import datetime as dt
from datetime import datetime, timedelta
from pre_backtest.trade_signal import SIGNAL
from pre_backtest.etf_roll import Target
from post_backtest.evaluate import evaluate
from tool.LazyChunk import LazyCsvGenerator
from tool.Tool import buy_stock
import json

import warnings
warnings.filterwarnings('ignore')

# 要使用的信号指标,参数
from setting import Fast_Indicator, Slow_Indicator, Moment_Indicator, Benchmark, coef
# 获取上交所交易日历
import exchange_calendars as ecals
calendar = ecals.get_calendar("XSHG")


# etf池
index_pool = ['上证180ETF', '中证500ETF', '黄金ETF']
index_code = ["510180", "510590", "518880"]
# indicator参数
coef = coef


# 初始股票库存
stock = None
stock_num = 0
# 佣金率
rate = 0.0002
discount_rate = 1-rate
# 初始资金
init_money = 3000
money = 3000

## 解决json序列化格式问题
def default_dump(obj):
    """Convert numpy classes to JSON serializable objects."""
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.values.tolist()
    elif isinstance(obj, (dt.date, dt.datetime)):
        return obj.strftime('%Y-%m-%d')
    else:
        raise TypeError(
            "Unserializable object {} of type {}".format(obj, type(obj))
        )

if __name__ == '__main__':
    # 回测范围
    # start_date = sys.argv[1] # 起始日期
    # end_date = sys.argv[2] # 结束日期
    start_date = '20250101'
    end_date = '20251127'



    benchmark_data = pd.read_excel(f'{project_root}/{Benchmark}.xlsx', index_col=0, header=0, parse_dates=['日期'])

    ## 1.创建一个分块数据迭代器和一个交易信号发射器
    data_loader = LazyCsvGenerator(f'{project_root}/{Benchmark}.csv')
    signal_generator = SIGNAL(data_loader, Fast_Indicator, Slow_Indicator, Moment_Indicator)

    # 初始化pre_signals(用于每天计算信号)
    pre_signals = [[[] for _ in range(len(Fast_Indicator)+len(Moment_Indicator))], "P", "P"]
    temp_dt = datetime.strptime(start_date, '%Y%m%d').date() - timedelta(days=100)
    init_date_range = calendar.sessions_in_range(temp_dt, start_date).date[-9:]
    for i, date in enumerate(init_date_range):
        signal_generator.alarm(date, coef, pre_signals, False)
    del temp_dt
    del init_date_range

    ## 2.获取股票池数据(分块数据迭代器)
    data_dict = {}
    for index in index_pool:
        data_dict[index] = LazyCsvGenerator(f'{project_root}/{index}.csv')
    index_selection = Target(data_dict, Slow_Indicator) #最优标的选择器

    ## 3.获得回测区间交易日日历
    date_range = calendar.sessions_in_range(start_date, end_date)
    date_range = date_range.date


    ## 4.开始回测
    res = pd.DataFrame(columns=['date']+
                               list(map(lambda x : 'fast_'+x, Fast_Indicator))+
                               list(map(lambda x : 'slow_'+x, Slow_Indicator))+
                               list(map(lambda x: 'moment_' + x, Moment_Indicator)) +
                               ['fast_inverse','moment_inverse','signal','best_etf','open_price','end_stock','stock_num','money'])

    for i, date in enumerate(date_range):
        # 当天信号
        signal = signal_generator.alarm(date, coef, pre_signals)
        # 当天最优etf标的
        index = index_selection.get_best_target(date, coef)
        index_open_price = index_selection.normal_current_view[index].loc[date, '开盘'] # 由于动量数据只获取到T-1天的，而normal_current_view包含T天数据
        # 当天log
        log = [date,*signal,index,index_open_price,0,0,0]
        # 开盘时交易
        if signal[-1] == 'SELL':
            if stock is not None:
                today_open = index_selection.normal_current_view[stock].loc[date, '开盘']
                money += stock_num*today_open*discount_rate
            log[-1] = money
            log[-2] = 0
            log[-3] = None
            stock, stock_num = None, 0
        elif signal[-1] == 'BUY':
            if stock != index:
                if stock is not None:
                    today_open = index_selection.normal_current_view[stock].loc[date, '开盘']
                    money += stock_num * today_open * discount_rate
                stock_num, money = buy_stock(money, index_open_price, init_money, discount_rate, full_posotion=True)
                if stock_num != 0:
                    stock = index
            log[-1] = money
            log[-2] = stock_num
            log[-3] = stock
        else:
            if stock != index:
                if stock is not None:
                    today_open = index_selection.normal_current_view[stock].loc[date, '开盘']
                    money += stock_num * today_open * discount_rate
                stock_num, money = buy_stock(money, index_open_price, init_money, discount_rate, full_posotion=False)
                if stock_num != 0:
                    stock = index
            log[-1] = money
            log[-2] = stock_num
            log[-3] = stock
        res = pd.concat([res, pd.DataFrame(data=[log], index=[date], columns=res.columns)])

    ## 5.统计当天累计收益（截止开盘）
    benchmark_data = benchmark_data.loc[date_range]
    hs300_acc_yeild = (benchmark_data.iloc[-1]['开盘'] - benchmark_data.iloc[0]['开盘'])/benchmark_data.iloc[0]['开盘']
    res_all = res['stock_num'] * res['open_price'] + res['money']
    strategy_acc_yield = (res_all[-1]-res_all[0])/res_all[0]

    ## 6.今天收益
    hs300_today = (benchmark_data.iloc[-1]['收盘'] - benchmark_data.iloc[-1]['开盘'])/benchmark_data.iloc[-1]['开盘']
    index_selection._update_current_view(date_range[-1]) # 更新到-2天etf数据
    strategy_today_index = res.iloc[-1,-3] # -1天开盘持有的etf
    strategy_today_index_num = res.iloc[-1,-2] # -1天开盘持有的etf的数量
    strategy_today_money = res.iloc[-1, -1]  # -1天开盘持有的money
    if strategy_today_index is None:
        strategy_today = 0
    else:
        data = index_selection.normal_current_view[strategy_today_index].iloc[-1] # 取到持有的etf的-1天数据
        strategy_today = (data['收盘'] - data['开盘']) * strategy_today_index_num / (strategy_today_money + strategy_today_index_num * data['开盘'])

    ## 7.生成明天信号
    signal = signal_generator.pred_alarm(date_range[-1], coef, pre_signals)
    index = index_selection.pred_get_best_target(date_range[-1], coef)

    ## 8.历史累计收益
    benchmark_data['yield rate'] = benchmark_data['开盘'].pct_change()
    benchmark_data.iloc[0, benchmark_data.columns.get_loc('yield rate')] = 0
    benchmark_data['accumulate yield'] = (benchmark_data['开盘'] - benchmark_data.iloc[0]['开盘']) / benchmark_data.iloc[0]['开盘']

    res['asset'] = res['stock_num'] * res['open_price'] + res['money']
    res['yield rate'] = res['asset'].pct_change()
    res.iloc[0, res.columns.get_loc('yield rate')] = 0
    res['accumulate yield'] = (res['asset'] - res.iloc[0]['asset']) / res.iloc[0]['asset']

    ## 9.总评价
    eva = evaluate(res['yield rate'], benchmark_data['yield rate'])

    ## 10.新增一个tomorrow_signal_confidence的计算方法(根据trade_signal规则演化而来)
    fast = signal[:5]
    slow = signal[5:8]
    moment = signal[8:11]
    inverse = signal[11:13]
    s = signal[-1]
    if s == 'SELL':
        conf = max(fast.count(-1)/5, slow.count(-1)/3, moment.count(-1)/3, 0.8 * (fast.count(-1)/5 + slow.count(-1)/3))
        conf = max(conf, inverse.count("N") * (1 - (fast.count(1)+moment.count(1)) / 16))
    elif s == 'BUY':
        conf = max(fast.count(1)/5, slow.count(1)/3, moment.count(1)/3, 0.8 * (fast.count(1)/5 + slow.count(1)/3))
    else:
        conf1 = min(fast.count(-1)/5, slow.count(-1)/3, moment.count(-1)/3, 0.8 * (fast.count(-1)/5 + slow.count(-1)/3))
        conf1 = min(conf1, inverse.count("N") * (1 - (fast.count(1) + moment.count(1)) / 16))
        conf2 = min(fast.count(1)/5, slow.count(1)/3, moment.count(1)/3, 0.8 * (fast.count(1)/5 + slow.count(1)/3))
        conf = (1-conf2)*(1-conf1)
    conf = round(conf*100,0)


    # 返回json
    print(
        json.dumps({
            "status": "success",
            "data": {
                "basic_metrics": {
                    "hs300_cumulative_return": hs300_acc_yeild * 100,
                    "strategy_cumulative_return": strategy_acc_yield * 100,
                    "hs300_today_return": hs300_today * 100,
                    "strategy_today_return": strategy_today * 100,
                    "tomorrow_signal": signal[-1],
                    "tomorrow_signal_confidence": conf,
                    "tomorrow_best_etf": {
                        "name": index,
                        "code": index_code[index_pool.index(index)]
                    },
                    "max_back_step": {
                        "value": eva['最大回撤'] * 100,
                        "date_range": {
                            "max_back_step_begin": eva['最大回测峰顶'],
                            "max_back_step_end": eva['最大回测峰谷']
                        }
                    },
                    "winning_rate": eva['胜率'],
                    "timestamp": date_range[-1]
                },
                "cumulative_returns": {
                    "date": date_range,
                    "hs300_returns": benchmark_data['accumulate yield'] * 100,
                    "strategy_returns": res['accumulate yield'] * 100
                }
            }
        }, default=default_dump)
    )