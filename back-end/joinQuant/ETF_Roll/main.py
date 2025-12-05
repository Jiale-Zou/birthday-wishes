import cProfile

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pre_backtest.trade_signal import SIGNAL
from pre_backtest.etf_roll import Target
from post_backtest.evaluate import evaluate
from tool.LazyChunk import LazyCsvGenerator
from tool.Tool import buy_stock
import matplotlib.pyplot as plt
import json

import openpyxl
from openpyxl.drawing.image import Image
import io
import warnings
warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 要使用的信号指标,参数
from setting import Fast_Indicator, Slow_Indicator, Moment_Indicator, Benchmark, coef
# 获取上交所交易日历
import exchange_calendars as ecals
calendar = ecals.get_calendar("XSHG")


# etf池
index_pool = ['上证180ETF', '中证500ETF', '黄金ETF']
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
        return obj.values
    else:
        return obj

if __name__ == '__main__':
    # 回测范围
    start_date = '2025-01-01'
    end_date = '2025-11-25'

    benchmark_data = pd.read_excel(f'../{Benchmark}.xlsx', index_col=0, header=0, parse_dates=['日期'])
    benchmark_data['current yield'] = benchmark_data['开盘'].pct_change()
    print(f"fast: {Fast_Indicator}; slow: {Slow_Indicator}; moment: {Moment_Indicator}; Benchmark: {Benchmark}")
    ## 1.创建一个分块数据迭代器和一个交易信号发射器
    data_loader = LazyCsvGenerator(f'../{Benchmark}.csv')
    signal_generator = SIGNAL(data_loader, Fast_Indicator, Slow_Indicator, Moment_Indicator)

    # 初始化pre_signals(用于每天计算信号)
    pre_signals = [[[] for _ in range(len(Fast_Indicator)+len(Moment_Indicator))], "P", "P"]
    temp_dt = datetime.strptime(start_date, '%Y-%m-%d').date() - timedelta(days=100)
    init_date_range = calendar.sessions_in_range(temp_dt, start_date).date[-9:]
    for i, date in enumerate(init_date_range):
        signal_generator.alarm(date, coef, pre_signals, False)
    del temp_dt
    del init_date_range

    print('1.获取基准数据结束')
    ## 2.获取股票池数据(分块数据迭代器)
    data_dict = {}
    for index in index_pool:
        data_dict[index] = LazyCsvGenerator(f'../{index}.csv')
    index_selection = Target(data_dict, Slow_Indicator) #最优标的选择器
    print('2.获取股票池数据结束')
    ## 3.获得回测区间交易日日历
    date_range = calendar.sessions_in_range(start_date, end_date)
    date_range = date_range.date
    print('3.获得回测区间结束')
    ## 4.开始回测
    res = pd.DataFrame(columns=['date']+
                               list(map(lambda x : 'fast_'+x, Fast_Indicator))+
                               list(map(lambda x : 'slow_'+x, Slow_Indicator))+
                               list(map(lambda x: 'moment_' + x, Moment_Indicator)) +
                               ['fast_inverse','moment_inverse','signal','best_etf','open_price','end_stock','stock_num','money'])
    print('4.开始回测：')
    #profiler = cProfile.Profile()
    #profiler.enable()
    print('--------------------------')
    for i, date in enumerate(date_range[:-1]):
        # 今天的交易日日期
        print(f'  日期:{date}',end=' ')
        # 当天信号
        signal = signal_generator.alarm(date, coef, pre_signals)
        print(f'信号:{signal}', end=' ')
        # 当天最优etf标的
        index = index_selection.get_best_target(date, coef)
        index_selection._update_current_view(date_range[i+1]) #由于动量数据只获取到T-1天的，因此记录今天的情况需要更新到今天的数据
        index_open_price = index_selection.current_view[index].loc[date, '开盘']
        print(f'最优标的:{index}')
        # 当天log
        log = [date,*signal,index,index_open_price,0,0,0]
        # 开盘时交易
        if signal[-1] == 'SELL':
            if stock is not None:
                today_open = index_selection.current_view[stock].loc[date, '开盘']
                money += stock_num*today_open*discount_rate
            log[-1] = money
            log[-2] = 0
            log[-3] = None
            stock, stock_num = None, 0
        elif signal[-1] == 'BUY':
            if stock != index:
                if stock is not None:
                    today_open = index_selection.current_view[stock].loc[date, '开盘']
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
                    today_open = index_selection.current_view[stock].loc[date, '开盘']
                    money += stock_num * today_open * discount_rate
                stock_num, money = buy_stock(money, index_open_price, init_money, discount_rate, full_posotion=False)
                if stock_num != 0:
                    stock = index
            log[-1] = money
            log[-2] = stock_num
            log[-3] = stock
        res = pd.concat([res, pd.DataFrame(data=[log], index=[date], columns=res.columns)])
    print('回测结束----------------------')
    #profiler.disable()
    #profiler.print_stats(sort='cumtime')
    ## 5.绘制曲线
    date_range = date_range[:-1]
    benchmark_data = benchmark_data.loc[date_range]
    benchmark_data['yield rate'] = benchmark_data['开盘'].pct_change()
    benchmark_data.iloc[0, benchmark_data.columns.get_loc('yield rate')] = 0
    benchmark_data['accumulate yield'] = (benchmark_data['开盘'] - benchmark_data.iloc[0]['开盘'])/benchmark_data.iloc[0]['开盘']

    res['asset'] = res['stock_num'] * res['open_price'] + res['money']
    res['yield rate'] = res['asset'].pct_change()
    res.iloc[0, res.columns.get_loc('yield rate')] = 0
    res['accumulate yield'] = (res['asset']-res.iloc[0]['asset'])/res.iloc[0]['asset']
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(date_range, benchmark_data['accumulate yield'], label=Benchmark, color='b')
    ax1.plot(date_range, res['accumulate yield'], label='strategy', color='r')
    ax1.set_xlabel('date')
    ax1.set_ylabel('acc yield')
    ax1.set_title(str(index_pool))
    plt.legend(loc='upper right')
    buf = io.BytesIO() #将图片保存在内存中，不磁盘化
    plt.savefig(buf, format='png', dpi=300)
    plt.show()
    print('5.绘图成功')
    ## 6.返回回测结果
    with pd.ExcelWriter(f'../ETF_Roll backtest/{start_date}-{end_date}-{index_pool}.xlsx') as w:
        res.to_excel(excel_writer=w, index=False, header=True, sheet_name='backtest')
        evaluate(res['yield rate'], benchmark_data['yield rate']).to_excel(excel_writer=w,sheet_name='evaluate',header=False)
    json_coef = json.dumps(coef, default=default_dump)  # 将字典导出为json字符串
    xlsx = openpyxl.load_workbook(f'../ETF_Roll backtest/{start_date}-{end_date}-{index_pool}.xlsx')  # 读取xlsx文件
    table = xlsx.create_sheet('coef')  # 添加页
    table['A1'] = json_coef  # 设置单元格A1为参数
    table['A2'] = str(index_pool)
    buf.seek(0)
    img = Image(buf)  # 加载图片
    img.width = 500  # 像素
    img.height = 200
    table.add_image(img, 'A4')  # 将图片添加到A4单元格的位置
    xlsx.save(f'../ETF_Roll backtest/{start_date}-{end_date}-{index_pool}.xlsx')  # 一定要保存
    buf.close() #关闭内存
    print('6.数据已保存')
