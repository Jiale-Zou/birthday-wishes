from tool.LazyChunk import LazyCsvGenerator
from ETF_Roll.pre_backtest.trade_signal import SIGNAL
from ETF_Roll.pre_backtest.etf_roll import Target
from evaluate import evaluate, EVALUATE_INDEX
from tool.ParamSearchCV import RandomSearchCV
from tool.DistributedConnection import RedisQueue, RedisToXLSX
from tool.Tool import default_dump, buy_stock

import pandas as pd
from datetime import datetime, timedelta
from time import perf_counter
from concurrent.futures import ProcessPoolExecutor #进程池
from multiprocessing import Process #进程
import json
import signal
import warnings
warnings.filterwarnings('ignore')

import exchange_calendars as ecals
calendar = ecals.get_calendar("XSHG")

#要使用的信号指标
from ETF_Roll.setting import Fast_Indicator, Slow_Indicator, Moment_Indicator, coef_range, IF_DISTRIBUTED, start_date, end_date


### 回测，返回策略评价结果 ###
def backtest(coef, benchmark_yield_rate, rate, benchmark, date_range, money, stock=None, stock_num=0):
    print(coef)
    '''
    :param rate: 佣金率
    :param benchmark: 比较基准
    :param date_range: 回测区间
    :param coef: Indicator参数
    :param money: 初始资金
    :param stock: 初始库存，一般设为None
    :param stock_num: 初始库存数，stock为None就为0
    :return: a Series of evaluate
    '''
    discount_rate = 1-rate
    init_money = money
    res = pd.DataFrame(columns=['date', 'signal', 'best_etf', 'open_price', 'end_stock', 'stock_num', 'money'])
    ## 1.创建一个分块数据迭代器和一个交易信号发射器
    data_loader = LazyCsvGenerator(f'../../{benchmark}.csv')
    signal_generator = SIGNAL(data_loader, Fast_Indicator, Slow_Indicator, Moment_Indicator)

    # 初始化pre_signals(用于每天计算信号)
    pre_signals = [[[] for _ in range(len(Fast_Indicator)+len(Moment_Indicator))], "P", "P"]
    temp_dt = datetime.strptime(start_date, '%Y-%m-%d').date() - timedelta(days=100)
    init_date_range = calendar.sessions_in_range(temp_dt, start_date).date[-9:]
    for i, date in enumerate(init_date_range):
        signal_generator.alarm(date, coef, pre_signals, False)
    del temp_dt
    del init_date_range

    ## 2.创建标的数据字典
    data_dict = {}
    for index in index_pool:
        data_dict[index] = LazyCsvGenerator(f'../../{index}.csv')
    index_selection = Target(data_dict, Slow_Indicator)  # 最优标的选择器

    for i,date in enumerate(date_range[:-1]):
        # 当天信号
        signal = signal_generator.alarm(date, coef, pre_signals)
        # 当天最优etf标的
        index = index_selection.get_best_target(date, coef)
        index_selection._update_current_view(date_range[i + 1])  # 由于动量数据只获取到T-1天的，因此记录今天的情况需要更新到今天的数据
        index_open_price = index_selection.current_view[index].loc[date, '开盘']
        # 当天log
        log = [date, signal[-1], index, index_open_price, 0, 0, 0]
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
                stock_num, money = buy_stock(money, index_open_price,init_money,discount_rate,full_posotion=True)
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
                stock_num, money = buy_stock(money, index_open_price,init_money,discount_rate, full_posotion=False)
                if stock_num != 0:
                    stock = index
            log[-1] = money
            log[-2] = stock_num
            log[-3] = stock
        res = pd.concat([res, pd.DataFrame(data=[log], index=[date], columns=res.columns)])
    res['asset'] = res['stock_num'] * res['open_price'] + res['money']
    res['yield rate'] = res['asset'].pct_change()
    res.iloc[0, res.columns.get_loc('yield rate')] = 0

    test_evaluate = evaluate(res['yield rate'], benchmark_yield_rate)  # 回测评价
    test_evaluate['参数'] = json.dumps(coef, default=default_dump)
    return test_evaluate

### 如果是分布式计算，由于多进程要保证函数和参数Serializable。而函数要Serializable就得置顶，且不能文件句柄、数据库连接；参数要序列化就用default_dump函数 ###
# 因此，这里对backtest函数重构，使得在内部建立Redis的连接，而不是通过外部定义r=RedisQueue，再r.carry_out_task实现，导致not serializable
def new_backtest(backtest, other_params, pwd, ip='127.0.0.1', port=6379):
    # 创建RedisQueue对象，开启分布式计算
    new_r_queue = RedisQueue(ip, port, pwd)
    new_r_queue.carry_out_task(backtest, other_params)


# 佣金率
rate = 0.0002
# 比较基准
benchmark = '沪深300'
# 回测范围
start_date, end_date = start_date, end_date

# etf池
index_pool = ['上证180ETF', '中证500ETF', '黄金ETF']
# 初始资金
money = 3000

if __name__ == '__main__':
    # 交易日范围
    date_range = calendar.sessions_in_range(start_date, end_date)
    date_range = date_range.date
    # 基准数据
    benchmark_data = pd.read_excel(f'../../{benchmark}.xlsx', index_col=0, header=0, parse_dates=['日期'])
    benchmark_data['yield rate'] = benchmark_data['开盘'].pct_change()
    benchmark_data = benchmark_data.loc[date_range[1:-1]]['yield rate']

    # 搜索组合数
    n_iter = 500

    # 文件保存路径
    path = f'../../ETF_Roll backtest/参数搜索{start_date}-{end_date}-{index_pool}.xlsx'
    columns = EVALUATE_INDEX + ['参数']
    other_params = [benchmark_data,rate,benchmark,date_range,money,None,0]
    # 回测使用到的组合参数
    used_coef_range = {"fast": {key: coef_range["fast"][key] for key in coef_range["fast"].keys() if key.upper() in Fast_Indicator},
                  "slow": {key: coef_range["slow"][key] for key in coef_range["slow"].keys() if key.upper() in Slow_Indicator},
                "moment": {key: coef_range["moment"][key] for key in coef_range["moment"].keys() if key.upper() in Moment_Indicator}
                  }
    coef_comb = RandomSearchCV(used_coef_range, n_iter)

    # 使用多进程回测多个参数组合(if_distributed判断是否要使用分布式计算)
    def multiProcess_ifRedis(pwd, ip='127.0.0.1', port=6379, max_workers=10, if_distributed=False, is_master=False):
        if if_distributed: #开启分布式计算
            # 实时将Redis写入XLSX的（单独开一个线程）
            r_to_xlsx = RedisToXLSX(ip, port, pwd)
            # 注册信号处理(可以捕获键盘主动的Ctrl+C中断回测)
            signal.signal(signal.SIGINT, r_to_xlsx.signal_handler)
            signal.signal(signal.SIGTERM, r_to_xlsx.signal_handler)
            # 清理数据库
            r_to_xlsx.clear_database(only_used_keys=True)
            # 插入任务(如果为master节点)
            r_queue = RedisQueue(ip, port, pwd)
            if is_master: r_queue.input_task(coef_comb)
            del r_queue
            # 启动ReidsToXLSX
            writer_thread = r_to_xlsx.start_writing(path, result_count=n_iter, header=columns)

            # 开启多进程回测
            processes = []
            for _ in range(max_workers):
                p = Process(target=new_backtest, args=(backtest, other_params, pwd, ip, port))
                p.start()
                processes.append(p)
            for p in processes:
                p.join() # join() 方法会阻塞当前主进程，直到调用该方法的子进程执行完毕，防止任务还没有执行完就运行后面的代码

            # 阻塞调用它的线程，直至被调用的线程执行完毕（详细见"RedisToXLSX"内的说明）
            writer_thread.join()
        else:
            # 创建进程池
            executor = ProcessPoolExecutor(max_workers=max_workers)
            # 使用列表推导式一次性提交所有任务(避免直接获取result阻塞进程)
            futures = []
            for coef in coef_comb:
                if isinstance(coef, (str, int, float, bool)):
                    params = [coef] + other_params
                elif isinstance(coef, (list, tuple, set)):
                    params = list(coef) + other_params
                else:
                    params = [coef] + other_params
                futures.append(executor.submit(backtest, *params))
            # 在所有任务提交后，再收集结果
            written_header = True
            for future in futures:
                try:
                    result = future.result()
                except:
                    continue
                if written_header:
                    res = pd.DataFrame(columns=futures[0].result().index)
                    written_header = False
                res = pd.concat([res, result.to_frame().T], ignore_index=True)
            # 关闭进程池
            executor.shutdown()
            res.to_excel(path, index=True, header=True)

    pwd = input('输入Redis密码: ')
    start = perf_counter()
    multiProcess_ifRedis(pwd, if_distributed=IF_DISTRIBUTED, is_master=True)
    end = perf_counter()
    print(f'总耗时: {end - start:.04f}')