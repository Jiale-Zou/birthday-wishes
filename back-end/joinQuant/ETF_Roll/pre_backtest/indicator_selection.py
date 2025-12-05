import pandas as pd

from ETF_Roll.setting import Benchmark #基准曲线
from indicator import ProductFactory #指标库
from tool.ParamSearchCV import RandomSearchCV #随机参数搜索
from tool.TrendAnalyse import roll_window #标记基准曲线的上升区间和下降区间

from time import perf_counter
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

from ETF_Roll.setting import coef_range, start_date, end_date

# 获取上交所交易日历
import exchange_calendars as ecals
calendar = ecals.get_calendar("XSHG")
date_range = calendar.sessions_in_range(start_date, end_date)
date_range = date_range.date

'''
思路：
①先标记基准曲线的上升区间和下降区间
②对每个指标，进行随机参数搜索，并用单指标预测买卖信号，记录其最大预测能力时的参数和预测结果序列
③对第二步得到的单指标预测，进行各指标的组合，选择组合预测能力最大的组合，最为最终的指标选择
'''

# 参数搜索范围
coefs = coef_range

# 随机次数
n_iter = 1000

# 自定义函数，对于指标idc，参数coef，返回回测的得分F1及每天信号res
def single_signal(idc, coef, indicator_class, benchmark_data, used_range_data):
    res = pd.Series(index=date_range, name=idc)  # 记录当前参数下，指标idc的信号结果
    # 1.开始回测发送信号
    for date in date_range:
        indicator_class.data = benchmark_data.loc[:date].iloc[:-1]  # 更新数据视图至测试日前一天的数据
        # 得到get_函数
        func = getattr(indicator_class, f'get_{idc}')
        signal = func(**coef["get"])
        # 得到_jdg函数
        func = getattr(indicator_class, f'{idc}_jdg')
        if isinstance(signal, tuple):
            signal = func(*signal, **coef["jdg"])
        else:
            signal = func(signal, **coef["jdg"])
        res.loc[date] = signal
    # 2.根据回测结果与基准趋势比对，计算idc的coef参数F1得分
    TP_asc = ((used_range_data['Trend'] == 1) & (res == 1)).sum()
    if (res == 1).sum() > 0:
        P_asc = TP_asc / (res == 1).sum()
    else:
        P_asc = 0
    R_asc = TP_asc / (used_range_data['Trend'] == 1).sum()

    TP_desc = ((used_range_data['Trend'] == -1) & (res == -1)).sum()
    if (res == -1).sum() > 0:
        P_desc = TP_desc / (res == -1).sum()
    else:
        P_desc = 0
    R_desc = TP_desc / (used_range_data['Trend'] == -1).sum()

    TP_0 = ((used_range_data['Trend'] == 0) & (res == 0)).sum()
    if (res == 0).sum() > 0:
        P_0 = TP_0 / (res == 0).sum()
    else:
        P_0 = 0
    R_0 = TP_0 / (used_range_data['Trend'] == 0).sum()

    R = (R_asc + R_desc + R_0) / 3  # 多分类问题，用macro-F1
    P = (P_asc + P_desc + P_0) / 3
    F1 = 2 * P * R / (P + R)
    return idc, coef, F1, res

if __name__ == '__main__':
    t1 = perf_counter()
    ## 1.标记基准数据的上升、下降区间
    benchmark_data = pd.read_csv(f'../../{Benchmark}.csv', header=0, index_col=0, parse_dates=['日期'])
    asc_intervals, desc_intervals = roll_window(benchmark_data['开盘'])
    benchmark_data['Ascending'] = 0
    benchmark_data['Descending'] = 0
    for begin_date, end_date in asc_intervals:
        benchmark_data.loc[begin_date:end_date, 'Ascending'] = 1
    for begin_date, end_date in desc_intervals:
        benchmark_data.loc[begin_date:end_date, 'Descending'] = -1
    benchmark_data['Trend'] = benchmark_data['Ascending'] + benchmark_data['Descending']
    used_range_data = benchmark_data.loc[start_date:end_date].copy()
    print(f'1的比例: {(used_range_data['Trend'] == 1).sum()}, -1的比例: {(used_range_data['Trend'] == -1).sum()}, 0的比例: {(used_range_data['Trend'] == 0).sum()}')
    ## 2.对于每个指标，创建随机参数组合，并使用多进程开始回测
    fast_futures = []
    slow_futures = []
    moment_futures = []
    with ProcessPoolExecutor(20) as executor:
        for idc in coefs["fast"].keys():
            indicator_class = ProductFactory.create_product(idc, data=None)  # 创建指标实例
            coef_range = RandomSearchCV(coefs["fast"][idc], n_iter)  # 创建随机参数组合
            for coef in coef_range:
                fast_futures.append(executor.submit(single_signal, *[idc, coef, indicator_class, benchmark_data, used_range_data]))
        for idc in coefs["slow"].keys():
            indicator_class = ProductFactory.create_product(idc, data=None)
            coef_range = RandomSearchCV(coefs["slow"][idc], n_iter)
            for coef in coef_range:
                slow_futures.append(executor.submit(single_signal, *[idc, coef, indicator_class, benchmark_data, used_range_data]))
        for idc in coefs["moment"].keys():
            indicator_class = ProductFactory.create_product(idc, data=None)
            coef_range = RandomSearchCV(coefs["moment"][idc], n_iter)
            for coef in coef_range:
                moment_futures.append(executor.submit(single_signal, *[idc, coef, indicator_class, benchmark_data, used_range_data]))
    ## 3.根据结果记录最优回测结果
    best_performer = {"fast": {key: None for key in coefs["fast"].keys()},
                      "slow": {key: None for key in coefs["slow"].keys()},
                      "moment": {key: None for key in coefs["moment"].keys()}
                      }  # 记录各指标的最优表现时，每天的预测
    best_F1 = {"fast": {key: 0 for key in coefs["fast"].keys()},
               "slow": {key: 0 for key in coefs["slow"].keys()},
               "moment": {key: 0 for key in coefs["moment"].keys()}
               } # 记录各指标的最优表现时，F1得分
    best_coef = {"fast": {key: None for key in coefs["fast"].keys()},
                 "slow": {key: None for key in coefs["slow"].keys()},
                 "moment": {key: None for key in coefs["moment"].keys()}
                 } # 记录各指标的最优表现时，最优参数组合
    for future in fast_futures:
        res = future.result()
        if best_F1["fast"][res[0]] < res[2]:
            best_F1["fast"][res[0]] = res[2]
            best_performer["fast"][res[0]] = res[3]
            best_coef["fast"][res[0]] = res[1]
    for future in slow_futures:
        res = future.result()
        if best_F1["slow"][res[0]] < res[2]:
            best_F1["slow"][res[0]] = res[2]
            best_performer["slow"][res[0]] = res[3]
            best_coef["slow"][res[0]] = res[1]
    for future in moment_futures:
        res = future.result()
        if best_F1["moment"][res[0]] < res[2]:
            best_F1["moment"][res[0]] = res[2]
            best_performer["moment"][res[0]] = res[3]
            best_coef["moment"][res[0]] = res[1]

    print(f'各指标最优参数: {best_coef}')
    print(f'各指标最优得分: {best_F1}')

    t2 = perf_counter()
    print(f'总耗时: {t2-t1:.04f}秒')

    ## 4.选出最优指标
    selected_indicator = {"fast": [], "slow": [], "moment": []}
    for fs, items in best_F1.items():
        for key, score in items.items():
            if score > 0.5:
                selected_indicator[fs].append(key)
    print(f"选出的指标: {selected_indicator}")






