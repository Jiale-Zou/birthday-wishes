import numpy as np
import math

class RSRS:
    def __init__(self, data):
        self.data = data
        self.pre_slope = None # dp，用来计算之前的结果

    def ols(self, x, y):
        '''
        :param x: np.array
        :param y: np.array
        :return: ols (coefficients)
        '''
        beta, alpha = np.polyfit(x, y, 1)
        sse = y - (x * beta + alpha)
        r2 = 1 - np.dot(sse,sse) / ((len(x) - 1) * np.var(y))
        return beta, alpha, r2

    def get_slope_series(self, N, M):
        '''
        获得"沪深300"的斜率序列
        :param N: int (window range used to calculate slope)
        :param M: int (slope series size)
        :return: np.array (slope series)
        '''
        if self.pre_slope is None: # 在计算T天的slope_series时，可以复用T-1天已近计算的数据
            used_data = self.data.iloc[-(M+N-1):]
            series = [None]*M
            for i in range(M):
                beta, alpha, r2 = self.ols(used_data['最低'].iloc[i:i+N], used_data['最高'].iloc[i:i+N])
                series[i] = beta
            self.pre_slope = series
            return r2
        else:
            used_data = self.data.iloc[-N:]
            beta, alpha, r2 = self.ols(used_data['最低'], used_data['最高'])
            self.pre_slope.append(beta)
            return r2

    def z_score(self, slope_series):
        '''
        Standardize the end slope, thus help to estimate the distance between the end slope and the mean.
        :param slope_series:
        :return: end Z-score
        '''
        mean = np.mean(slope_series)
        std = np.std(slope_series)
        return (slope_series[-1]-mean)/std

    def get_rsrs(self, N=20, M=100):
        r2 = self.get_slope_series(N, M)
        return self.z_score(self.pre_slope[-M:]) * r2

    def rsrs_jdg(self, x, threshold=0.7):
        '''
        Generate rsrs signal according to threshold
        :param x: rsrs value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0

    def slow_rank_score(self, M, N=None):
        ''' SLOW
        get an index's score for ranking
        :param M: data range
        :return:
        '''
        used_data = self.data.iloc[-M:]
        coef = np.polyfit(used_data['最低'], used_data['最高'], 1)
        annualized_returns = math.pow(math.exp(np.round(coef[0], 4)), 250) - 1
        r2 = 1-sum((used_data['最高']-(used_data['最低']*coef[0]+coef[1])) ** 2) / ((1-len(used_data['最低']))*np.var(used_data['最高']))
        return annualized_returns * r2


class MA:
    def __init__(self, data):
        self.data = data

    def get_ma(self, N=3, M=20):
        '''
        Used to get today MA and befor MA
        :param N: int (window range used to calculate MA)
        :param M: int (gap between today MA and before MA)
        :return: today MA/before MA
        '''
        today_ma = self.data['收盘'].iloc[-M:].sum()
        before_ma = self.data['收盘'].iloc[-(N + M):-N].sum()
        return today_ma/before_ma

    def ma_jdg(self, today_ratio_before, criterion=1.005):
        '''
        Generate ma signal according to criterion
        :param today: today's ma value
        :param before: the day before today's ma value
        :param criterion:
        :return:
        '''
        if today_ratio_before >= criterion:
            return 1
        elif today_ratio_before <= 1/criterion:
            return -1
        else:
            return 0



class CCI:
    def __init__(self, data):
        self.data = data

    def get_cci(self, window=300):
        '''
        Used to calculate CCI of window range.
        :param window: CCI window range
        :return: today CCI
        '''
        tp = (self.data['最高'].iloc[-window:]+self.data['最低'].iloc[-window:]+self.data['收盘'].iloc[-window:])/3
        mean = tp.iloc[:-1].mean()
        std = tp.iloc[:-1].std()
        return (tp.iloc[-1]-mean)/(0.015*std)

    def cci_jdg(self, x, threshold=100):
        '''
        Generate cci signal according to threshold
        :param x: cci value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0


class MACD:
    def __init__(self, data):
        self.data = data

    def get_macd(self, rt_length, fast = 12, slow=26, signal=9):
        '''
        Used to calculate MACD
        :param rt_length: returned series' length
        :param fast: the fast line range(EMA)
        :param slow: the slow line range(EMA)
        :param signal: the signal range(DEA)
        :return: MACD series
        '''
        used_data = self.data.iloc[-(rt_length+signal+slow-2):]
        EMA_fast = (used_data['收盘'].iloc[-(rt_length+signal+fast-2):].ewm(span=fast, adjust=False).mean()).iloc[-(rt_length+signal-1):]
        EMA_slow = (used_data['收盘'].ewm(span=slow, adjust=False).mean()).iloc[-(rt_length+signal-1):]
        DIF = EMA_fast - EMA_slow
        DEA = DIF.ewm(span=signal, adjust=False).mean()
        MACD_hist = (DIF-DEA).iloc[-rt_length:]
        return MACD_hist

    def macd_jdg(self, x, placeholder=None):
        '''
        Generate macd signal according to criterion
        :param x: macd series
        :return:
        '''
        if x[-1] >= 0 and (x[-1] > x.mean() or len(x) == 1):
            return 1
        elif x[-1] <= 0 and (x[-1] < x.mean() or len(x) == 1):
            return -1
        else:
            return 0



class IDR:
    '''IDR: 隔夜因子'''
    '''短期内与收益正相关，长期内负相关'''
    def __init__(self, data):
        self.data = data
        self.pre_slope = None

    def ols(self, x, y):
        '''
        :param x: np.array
        :param y: np.array
        :return: ols (coefficients)
        '''
        coef = np.polyfit(x, y, 1)
        sse = y - (x * coef[0] + coef[1])
        r2 = 1 - np.dot(sse,sse) / ((1 - len(x)) * np.var(y))
        return coef[0], coef[1], r2

    def get_slope_series(self, N, M):
        '''
        获得"沪深300"的斜率序列
        :param N: int (window range used to calculate slope)
        :param M: int (slope series size)
        :return: np.array (slope series)
        '''
        if self.pre_slope is None:
            used_data = self.data.iloc[-(M + N):].copy() # .loc和.iloc对于连续索引只是返回视图，用.copy()显示返回副本
            used_data['intraday'] = used_data['收盘'].shift(1)
            used_data.drop(index = used_data.index[0], inplace = True)
            series = [None]*M
            for i in range(M):
                beta, alpha, r2 = self.ols(used_data['intraday'].iloc[i:i + N], used_data['开盘'].iloc[i:i + N])
                series[i] = beta
            self.pre_slope = series
            return r2
        else:
            used_data = self.data.iloc[-(N+1):].copy()
            used_data['intraday'] = used_data['收盘'].shift(1)
            used_data.drop(index = used_data.index[0], inplace = True)
            beta, alpha, r2 = self.ols(used_data['intraday'], used_data['开盘'])
            self.pre_slope.append(beta)
            return r2

    def z_score(self, slope_series):
        '''
        Standardize the end slope, thus help to estimate the distance between the end slope and the mean.
        :param slope_series:
        :return: end Z-score
        '''
        mean = np.mean(slope_series)
        std = np.std(slope_series)
        return (slope_series[-1]-mean)/std

    def get_idr(self, N=18, M=300):
        r2 = self.get_slope_series(N, M)
        return self.z_score(self.pre_slope[-M:]) * r2

    def idr_jdg(self, x, threshold=0.7):
        '''
        Generate cci signal according to threshold
        :param x: cci value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0

    def slow_rank_score(self, M, N=None):
        '''SLOW
        get an index's score for ranking
        :param M:
        :param N:
        :return:
        '''
        used_data = self.data.iloc[-(M+1):].copy()
        used_data['intraday'] = used_data['收盘'].shift(1)
        used_data.drop(index=used_data.index[0], inplace=True)
        coef = np.polyfit(used_data['intraday'], used_data['开盘'], 1)
        annualized_returns = math.pow(math.exp(np.round(coef[0], 4)), 250) - 1
        r2 = 1-sum((used_data['开盘']-(used_data['intraday']*coef[0]+coef[1]))**2)/((1-len(used_data['intraday']))*np.var(used_data['开盘']))
        return annualized_returns * r2

class ADX:
    '''ADX: 平均方向动量指标'''
    def __init__(self, data):
        self.data = data

    def get_adx(self, N=14):
        used_data = self.data.iloc[-(N + N):].copy()
        used_data['intraday_close'] = used_data['收盘'].shift(1)
        used_data['intraday_low'] = used_data['最低'].shift(1)
        used_data['intraday_high'] = used_data['最高'].shift(1)
        used_data.drop(index=used_data.index[0], inplace=True)
        used_data['TR'] = np.maximum(used_data['最高']-used_data['最低'], np.abs(used_data['最高']-used_data['intraday_close']), np.abs(used_data['最低']-used_data['intraday_close']))
        used_data['ATR'] = used_data['TR'].rolling(window=N, center=False).mean()
        used_data['+DM'] = np.where(used_data['最高']-used_data['intraday_high'] > 0, used_data['最高']-used_data['intraday_high'], 0)
        used_data['+ADM'] = used_data['+DM'].rolling(window=N, center=False).mean()
        used_data['-DM'] = np.where(used_data['intraday_low']-used_data['最低'] > 0, used_data['intraday_low']-used_data['最低'], 0)
        used_data['-ADM'] = used_data['-DM'].rolling(window=N, center=False).mean()
        used_data.dropna(subset=['ATR'], inplace=True)
        used_data['+DI'] = used_data['+ADM'] / used_data['ATR']
        used_data['-DI'] = used_data['-ADM'] / used_data['ATR']
        used_data['DX'] = (used_data['+DI'] - used_data['-DI']) / (used_data['+DI'] + used_data['-DI'])
        return used_data['DX'].mean()*100

    def adx_jdg(self, x, threshold=50):
        '''
        Generate adx signal according to threshold
        :param x: adx value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0



class BOLL:
    '''BOLL: 布林线'''
    def __init__(self, data):
        self.data = data

    def get_boll(self, window=300):
        '''
        Used to calculate BOLL of window range.
        :param window: COLL window range
        :return: mean, std
        '''
        used_data = self.data.iloc[-(window):]['收盘']
        mean = used_data.iloc[:-1].mean()
        std = used_data.iloc[:-1].std()
        return mean, std, used_data.iloc[-1]

    def boll_jdg(self, mean, std, val, pct=2):
        '''
        Generate BOLL signal according to threshold
        :param mean: window days' mean
        :param std: window days' std'
        :param val: yesterday's close price
        :param pct: how many multiple of std used to calculate top and bottom boll line
        :return:
        '''
        if val >= mean + pct * std:
            return 1
        elif val <= mean - pct * std:
            return -1
        else:
            return 0


class OBV:
    '''OBV: 能量潮'''
    '''OBV由累计成交量得到，这里对累计成交量与收盘价比值得到OBV'''
    def __init__(self, data):
        self.data = data
        self.pre_slope = None

    def ols(self, x, y):
        '''
        :param x: np.array
        :param y: np.array
        :return: ols (coefficients)
        '''
        coef = np.polyfit(x, y, 1)
        sse = y - (x * coef[0] + coef[1])
        r2 = 1 - np.dot(sse,sse) / ((1 - len(x)) * np.var(y))
        return coef[0], coef[1], r2

    def get_slope_series(self, N=18, M=250):
        '''
        :param N: int (window range used to calculate slope)
        :param M: int (slope series size)
        :return: np.array (slope series)
        '''
        if self.pre_slope is None:
            used_data = self.data.iloc[-(M + N):].copy() # .loc和.iloc对于连续索引只是返回视图，用.copy()显示返回副本
            used_data['intraday_close'] = used_data['收盘'].shift(1)
            used_data.drop(index = used_data.index[0], inplace = True)
            used_data['plus_or_minus'] = np.sign(used_data['收盘'] - used_data['intraday_close']) * used_data['成交量']
            used_data.loc[used_data.index[0], 'plus_or_minus'] = used_data.iloc[0]['成交量']
            used_data['acc_balance'] = np.cumsum(used_data['plus_or_minus'])
            used_data['OBV'] = used_data['acc_balance'] / used_data['收盘']
            x = np.arange(N)
            series = [None]*M
            for i in range(M):
                beta, alpha, r2 = self.ols(x, used_data['OBV'].iloc[i:i + N]/used_data['OBV'].iloc[i]) # 除第一个值，消除量纲的影响
                series[i] = beta
            self.pre_slope = series
            return r2
        else:
            used_data = self.data.iloc[-(N + 1):].copy()
            used_data['intraday_close'] = used_data['收盘'].shift(1)
            used_data.drop(index=used_data.index[0], inplace=True)
            used_data['plus_or_minus'] = np.sign(used_data['收盘'] - used_data['intraday_close']) * used_data['成交量']  # sign数学函数
            used_data.loc[used_data.index[0], 'plus_or_minus'] = used_data.iloc[0]['成交量']
            used_data['acc_balance'] = np.cumsum(used_data['plus_or_minus'])
            used_data['OBV'] = used_data['acc_balance'] / used_data['收盘']
            used_data['OBV'] = used_data['OBV'] / used_data['OBV'].iloc[0]  # 除第一个值，消除量纲的影响
            x = np.arange(N)
            beta, alpha, r2 = self.ols(x, used_data['OBV'])
            self.pre_slope.append(beta)
            return r2

    def z_score(self, slope_series):
        '''
        Standardize the end slope, thus help to estimate the distance between the end slope and the mean.
        :param slope_series:
        :return: end Z-score
        '''
        mean = np.mean(slope_series)
        std = np.std(slope_series)
        return (slope_series[-1] - mean) / std

    def get_obv(self, N=18, M=150):
        r2 = self.get_slope_series(N, M)
        return self.z_score(self.pre_slope[-M:]) * r2

    def obv_jdg(self, x, threshold=1.2):
        '''
        Generate obv signal according to threshold
        :param x: obv value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0

    def slow_rank_score(self, M, N=None):
        '''SLOW
        get an index's score for ranking
        :param M:
        :param N:
        :return:
        '''
        used_data = self.data.iloc[-(N + 1):].copy()
        used_data['intraday_close'] = used_data['收盘'].shift(1)
        used_data.drop(index=used_data.index[0], inplace=True)
        used_data['plus_or_minus'] = np.sign(used_data['收盘'] - used_data['intraday_close']) * used_data['成交量']  # sign数学函数
        used_data.loc[used_data.index[0], 'plus_or_minus'] = used_data.iloc[0]['成交量']
        used_data['acc_balance'] = np.cumsum(used_data['plus_or_minus'])
        used_data['OBV'] = used_data['acc_balance'] / used_data['收盘']
        used_data['OBV'] = used_data['OBV'] / used_data['OBV'].iloc[0]  # 除第一个值，消除量纲的影响
        x = np.arange(N)
        coef = np.polyfit(x, used_data['OBV'], 1)
        annualized_returns = math.pow(math.exp(coef[0]/100), 250) - 1  #这里除100，是因为OBV这里算出的斜率很多>1
        r2 = 1-sum((used_data['OBV'] - (x * coef[0] + coef[1])) ** 2) / ((1 - len(x)) * np.var(used_data['OBV']))
        return annualized_returns * r2



class MFI:
    ''' MFI: 资金流量指标 '''
    def __init__(self, data):
        self.data = data

    def get_mfi(self, N=20):
        '''
        Used to calculate MFI of window range.
        :param window: MFI window range
        :return: today MFI
        '''
        used_data = self.data.iloc[-(N+1):].copy()
        used_data['tp'] = (used_data['最高'] + used_data['最低'] + used_data['收盘']) / 3
        used_data['intraday_tp'] = used_data['tp'].shift(1)
        used_data.drop(index=used_data.index[0], inplace=True)
        used_data['mf'] = np.multiply(used_data['tp'], used_data['成交量'])
        used_data['+mf'] = np.where(used_data['tp'] > used_data['intraday_tp'], used_data['mf'], 0)
        used_data['-mf'] = np.where(used_data['tp'] <= used_data['intraday_tp'], used_data['mf'], 0)
        pos_mf = np.sum(used_data['+mf'])
        neg_mf = np.sum(used_data['-mf'])
        mf_ratio = pos_mf / neg_mf
        return 100 - (100 / (1 + mf_ratio))

    def mfi_jdg(self, x, threshold=66):
        '''
        Generate mfi signal according to threshold
        :param x: obv value
        :param threshold:
        :return:
        '''
        if x > threshold:
            return 1
        elif x < -threshold:
            return -1
        else:
            return 0


class WPM:
    ''' WPM: 威廉指标 '''
    def __init__(self, data):
        self.data = data
        self.pre_wpm = None
    # N=29, M=304, threshold=0.33
    def get_wpm(self, N=21, M=250):
        if self.pre_wpm is None:
            used_data = self.data.iloc[-(M + N):]
            series = [None]*(M+1)
            for i in range(M+1):
                minimum = np.min(used_data.iloc[i:i+N]['最低'])
                maximum = np.max(used_data.iloc[i:i+N]['最高'])
                series[i] = (maximum - used_data.iloc[i+N-1]['收盘']) / (maximum - minimum)
            self.pre_wpm = series
            return self.pre_wpm[-1]/np.mean(self.pre_wpm[-(M+1):-1])
        else:
            used_data = self.data.iloc[-N:]
            minimum = np.min(used_data['最低'])
            maximum = np.max(used_data['最高'])
            self.pre_wpm.append((maximum - used_data.iloc[-1]['收盘']) / (maximum - minimum))
            return self.pre_wpm[-1] / np.mean(self.pre_wpm[-(M + 1):-1])

    def wpm_jdg(self, x, threshold=0.003):
        '''
        Generate wpm signal according to threshold
        :param x: wpm value
        :param threshold:
        :return:
        '''
        if x < 1-threshold:
            return 1
        elif x > 1+threshold:
            return -1
        else:
            return 0



class AD:
    ''' AD: 累积/派发量价指标 '''
    ''' 这里用M天的移动平均，并采用ma的评判方法 '''
    def __init__(self, data):
        self.data = data

    def get_ad(self, N=10, M=39):
        ad = self.data['成交量'] * (2 * self.data['收盘'] - self.data['最高'] - self.data['最低']) / (
                            self.data['最高'] - self.data['最低'])
        today_ad = np.sum(ad.iloc[-M:])
        before_ad = np.sum(ad.iloc[-(M+N):-N])
        return today_ad/before_ad

    def ad_jdg(self, today_ratio_before, criterion=1.01):
        '''
        Generate ad signal according to criterion+
        :param today: today's ad value
        :param before: the day before today's ad value
        :param criterion:
        :return:
        '''
        if today_ratio_before >= criterion:
            return 1
        elif today_ratio_before <= 1/criterion:
            return -1
        else:
            return 0



class ProductFactory:
    _products = {
        'RSRS': RSRS,
        'MA': MA,
        'CCI': CCI,
        'MACD': MACD,
        'IDR': IDR,
        'ADX': ADX,
        'BOLL': BOLL,
        'OBV': OBV,
        'MFI': MFI,
        'WPM': WPM,
        'AD': AD
    }
    @classmethod
    def create_product(cls, product_type: str, **kwargs):
        '''类生产工厂，用来根据输入字符串product_type创建对应的类'''
        product_class = cls._products.get(product_type.upper()) #要创建的类
        if not product_class:
            raise ValueError(f"Unknown product type: {product_type}")
        # 验证必需参数
        required_params = product_class.__annotations__.keys()
        missing = [p for p in required_params if p not in kwargs]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        return product_class(**kwargs)


#index_zh_a_hist(symbol='000300', period="daily",start_date='20200101',end_date='20241231')
#fund_etf_hist_em(symbol="159561", period="daily", start_date="20200101", end_date="20241231", adjust="")
