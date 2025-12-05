import pandas as pd
import numpy as np
import math

EVALUATE_INDEX = ['累计收益率', '年化收益率', '日度收益率', '超额收益', '基准收益', '胜率', '缺席率', '盈亏比', '最大回撤', '最大回测峰顶', '最大回测峰谷',
         '夏普比率', '信息比率', '策略波动率', '基准波动率']

def evaluate(strategy_series,benchmark_series):
    '''
    :param series: the every yield series
    :return: comprehensive evaluating indicator
    '''
    res = pd.Series()
    cum_yield = 1 # 累计收益率(只有累计收益率考虑了佣金)
    win = 0 #赢数
    lose = 0 #输数
    absence = 0 #缺席数
    win_amount= 0 #赢总额
    lose_amount = 0 #亏总额
    max_traceback = 0 #最大回撤
    pre_max_cum_yield = 1 #当前最大的累计收益率
    pre_max_cum_yield_date = strategy_series.index[0] #当前最大的累计收益率的日期
    max_traceback_peak_date = None #最大回测顶部的日期
    max_traceback_bottom_date = None #最大回测底部的日期
    inform_ratio = [None] * len(strategy_series) #策略与基准每日收益率差，用来计算信息比率
    # 1.策略收益指标
    for i,x in enumerate(strategy_series):
        # 计算胜率和盈亏比
        if x > 0:
            win += 1
            win_amount += cum_yield*x
        elif x < 0:
            lose += 1
            lose_amount += cum_yield*x
        else:
            absence += 1
        # 计算累计收益率
        cum_yield *= (1 + strategy_series[i])
        # 更新最大回测和当前最大的累计收益率
        if cum_yield-pre_max_cum_yield < max_traceback:
            max_traceback = cum_yield-pre_max_cum_yield
            max_traceback_bottom_date = strategy_series.index[i]
            max_traceback_peak_date = pre_max_cum_yield_date
        if cum_yield > pre_max_cum_yield:
            pre_max_cum_yield = cum_yield
            pre_max_cum_yield_date = strategy_series.index[i]
        # 记录信息比率
        inform_ratio[i] = strategy_series[i] - benchmark_series[i]
    bcm_cum_yield = 1
    # 2.基准累计收益率
    for x in benchmark_series:
        bcm_cum_yield *= (1 + x)

    res['累计收益率'] = cum_yield-1
    res['年化收益率'] = math.pow((1+res['累计收益率']),250/len(strategy_series))-1
    res['日度收益率'] = math.pow(1+res['年化收益率'], 1/250)-1
    res['超额收益'] = cum_yield - bcm_cum_yield
    res['基准收益'] = bcm_cum_yield-1
    res['胜率'] = win/(win+lose)
    res['缺席率'] = absence/(win+lose+absence)
    res['盈亏比'] = win_amount/abs(lose_amount)
    res['最大回撤'] = max_traceback
    res['最大回测峰顶'] = max_traceback_peak_date.strftime('%Y-%m-%d')
    res['最大回测峰谷'] = max_traceback_bottom_date.strftime('%Y-%m-%d')
    res['夏普比率'] = (res['年化收益率']-0.04)/np.std(list(map(lambda x:math.pow(x+1, 250)-1, strategy_series)))
    res['信息比率'] = (math.pow((1+cum_yield-bcm_cum_yield),250/len(strategy_series))-1)/np.std(list(map(lambda x:math.pow(x+1, 250)-1, inform_ratio)))
    res['策略波动率'] = np.sqrt(np.var(strategy_series)*250)
    res['基准波动率'] = np.sqrt(np.var(benchmark_series)*250)

    return res
