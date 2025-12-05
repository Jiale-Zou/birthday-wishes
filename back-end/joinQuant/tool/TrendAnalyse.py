import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def roll_window(data, windows=20, length=20, threshold=15, pct = 0.15):
    '''
    用来得到时间序列data中具有明显趋势（上升或下降）的区间范围（左闭右开）
    :param data: 输入的时间序列数据
    :param windows: 计算斜率的窗口的长度
    :param length: 平滑斜率的窗口的长度
    :param threshold: 在length窗口中，平滑后为正斜率需要的正斜率数
    :param pct: 连接几个小区间时，中间间隔不超过连接后总长度的百分比的阈值
    :return:
    '''
    # 先滑动平均原数据过滤噪声
    data = data.rolling(window=5, min_periods=1, center=False).mean()
    n = len(data)
    half = length//2
    x = np.arange(windows)
    # 计算滑动区间的斜率
    slopes = [0]*(n-windows+1)
    for i in range(n-windows+1):
        slopes[i] = np.polyfit(x, data[i:i+windows], 1)[0]
    # 平滑斜率
    smooth_slopes_asc = [False]*(n-windows+1)
    smooth_slopes_desc = [False] * (n-windows+1)
    cnt_asc = 0
    cnt_desc = 0
    for i in range(length-1):
        cnt_asc += (slopes[i] > 0)
        cnt_desc += (slopes[i] < 0)
    for i in range(half, n-windows+1-half):
        cnt_asc += (slopes[i+half] > 0)
        cnt_desc += (slopes[i+half] < 0)
        smooth_slopes_asc[i] = (cnt_asc >= threshold)
        smooth_slopes_desc[i] = (cnt_desc >= threshold)
        cnt_asc -= (slopes[i-half] > 0)
        cnt_desc -= (slopes[i-half] < 0)
    # 找到连续长区间
    res_asc, res_desc = [], [] #最后返回的区间
    left_asc, left_desc = None, None
    for i in range(n-windows+1):
        if smooth_slopes_asc[i] and not left_asc:
            left_asc = i
        elif not smooth_slopes_asc[i] and left_asc:
            if len(res_asc) > 0:
                l_border_asc,r_border_asc = res_asc[-1]
                if (i+windows-1-l_border_asc) * pct > (left_asc+windows-1-r_border_asc) and (left_asc-i) >= (left_asc+windows-1-r_border_asc) and (r_border_asc-l_border_asc) >= (left_asc+windows-1-r_border_asc):
                    res_asc[-1] = (l_border_asc, i+windows-1)
                else:
                    res_asc.append((left_asc + windows - 1, i + windows - 1))
            else:
                res_asc.append((left_asc+windows-1, i+windows-1))
            left_asc = None
        if smooth_slopes_desc[i] and not left_desc:
            left_desc = i
        elif not smooth_slopes_desc[i] and left_desc:
            if len(res_desc) > 0:
                l_border_desc, r_border_desc = res_desc[-1]
                if (i + windows - 1 - l_border_desc) * pct > (left_desc + windows - 1 - r_border_desc) and (left_desc-i) >= (left_desc+windows-1-r_border_desc) and (r_border_desc-l_border_desc) >= (left_desc+windows-1-r_border_desc):
                    res_desc[-1] = (l_border_desc, i + windows - 1)
                else:
                    res_desc.append((left_desc + windows - 1, i + windows - 1))
            else:
                res_desc.append((left_desc + windows - 1, i + windows - 1))
            left_desc = None

    def index_to_date(tup):
        '''将数值索引映射为原有的索引'''
        return data.index[tup[0]], data.index[tup[1]]

    return list(map(index_to_date, res_asc)),list(map(index_to_date, res_desc))


def plot_trend(benchmark='沪深300',trend='升'):
    '''
    用来可视化时间序列的具有趋势的区间
    :param benchmark: 时间序列指标
    :param trend: 选择画出升趋势区间还是降趋势区间
    :return:
    '''
    data = pd.read_excel(f'..\\{benchmark}.xlsx', index_col=0, parse_dates=['日期'])['开盘']
    if trend == '升':
        trend = 0
    else:
        trend = 1
    intervals = roll_window(data)[trend]
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 5))

    # 绘制时间序列
    ax.plot(data.index, data, 'b-', linewidth=1, label='数据')

    # 为每个区间的起点和终点添加竖线
    for i, (start, end) in enumerate(intervals):
        # 转换为datetime对象（如果尚未转换）
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)

        # 添加竖线
        ax.axvline(start, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
        ax.axvline(end, color='green', linestyle='--', linewidth=0.8, alpha=0.7)

        # 可选：添加区间标签
        ax.text(start, ax.get_ylim()[1] * 0.95, f'区间{i + 1}开始',
                rotation=90, va='top', ha='right', color='red', fontsize=8)
        ax.text(end, ax.get_ylim()[1] * 0.95, f'区间{i + 1}结束',
                rotation=90, va='top', ha='left', color='green', fontsize=8)

    # 优化日期显示
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()  # 自动旋转日期标签

    # 添加图例和标题
    ax.set_title(f'时间序列与区间边界标记-{"升" if trend == 0 else "降"}', fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.show()

