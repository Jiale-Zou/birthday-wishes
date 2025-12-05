from tool.LazyChunk import LazyCsvGenerator
from ETF_Roll.pre_backtest.indicator import ProductFactory

import numpy as np

class SIGNAL:
    def __init__(self, data_loader: LazyCsvGenerator, fast_signals, slow_signals, moment_signals):
        self._data_loader = data_loader #数据迭代器
        self.current_view = None #当前数据视图，即每次只更新数据视图，而不使用底层数据
        self.normal_current_view = None #current_view包含T-1天数据，而normal_current_view包含T天数据
        # 实例化使用的信号指标类
        self.fast_signal_indicators = [ProductFactory.create_product(s, data=None) for s in fast_signals] #短线指标
        self.slow_signal_indicators = [ProductFactory.create_product(s, data=None) for s in slow_signals] #长线指标
        self.moment_signal_indicators = [ProductFactory.create_product(s, data=None) for s in moment_signals] #瞬时指标

        self.fast_n = len(self.fast_signal_indicators)
        self.slow_n = len(self.slow_signal_indicators)
        self.moment_n = len(self.moment_signal_indicators)

    def _update_current_view(self, date):
        '''
        Update the self.current_view according to the date
        :param date: the end date you want to end before
        :return:
        '''
        try:
            if self.current_view is None: # 初始化时，先加载到初始日期的数据块
                self._data_loader._load_chunk_to_date(date)
            elif self._data_loader.preloaded_data.index[-1] < date:  # 若要使用的日期大于当前加载的数据，则再加载一个数据块
                self._data_loader._load_next_chunk()
        except StopIteration:
            raise StopIteration("Error: date out of data's range")
        self.normal_current_view = self._data_loader.preloaded_data.loc[:date]
        self.current_view = self.normal_current_view.iloc[:-1] # 根据日期更新视图（loc比iloc更快）（loc是闭区间，iloc是开区间）

    def alarm(self, date, coef_dict, pre_signals, flag=True):
        '''
        Used to get the full quantitative signal
        :date: the signal date
        :coef_dict: the indicator coefficient dictionary
        :pre_signals: record the pre signals, used to calculate today's signal
        :flag: whether consider the pre_signals when calculate today's signal
        :return: SELL, KEEP or BUY
        '''
        try:
            self._update_current_view(date) # 先更新一下今天的数据视图
        except StopIteration:
            raise StopIteration("Error: date out of data's range")

        ## 更新信号指标实例类使用的数据
        for i in range(self.fast_n):
            self.fast_signal_indicators[i].data = self.current_view
        for i in range(self.slow_n):
            self.slow_signal_indicators[i].data = self.current_view
        for i in range(self.moment_n):
            self.moment_signal_indicators[i].data = self.current_view
        ## 根据参数生成对应信号(短线指标)
        fast_indicator_signals = [0]*self.fast_n
        for i in range(self.fast_n):
            cls_name = type(self.fast_signal_indicators[i]).__name__.lower() #type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.fast_signal_indicators[i], f'get_{cls_name}') #得到信号类_get形式的方法
                signal = func(**coef_dict["fast"][cls_name]["get"]) #调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.fast_signal_indicators[i], f'{cls_name}_jdg') #得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    fast_indicator_signals[i] = func(*signal, **coef_dict["fast"][cls_name]["jdg"]) #调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    fast_indicator_signals[i] = func(signal, **coef_dict["fast"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")
        ## 根据参数生成对应信号(长线指标)
        slow_indicator_signals = [0] * self.slow_n
        for i in range(self.slow_n):
            cls_name = type(self.slow_signal_indicators[i]).__name__.lower()  # type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.slow_signal_indicators[i], f'get_{cls_name}')  # 得到信号类_get形式的方法
                signal = func(**coef_dict["slow"][cls_name]["get"])  # 调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.slow_signal_indicators[i], f'{cls_name}_jdg')  # 得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    slow_indicator_signals[i] = func(*signal, **coef_dict["slow"][cls_name]["jdg"])  # 调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    slow_indicator_signals[i] = func(signal, **coef_dict["slow"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")
        ## 根据参数生成对应信号(冲量指标)
        moment_indicator_signals = [0] * self.moment_n
        for i in range(self.moment_n):
            cls_name = type(self.moment_signal_indicators[i]).__name__.lower()  # type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.moment_signal_indicators[i], f'get_{cls_name}')  # 得到信号类_get形式的方法
                signal = func(
                    **coef_dict["moment"][cls_name]["get"])  # 调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.moment_signal_indicators[i], f'{cls_name}_jdg')  # 得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    moment_indicator_signals[i] = func(*signal, **coef_dict["moment"][cls_name]["jdg"])  # 调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    moment_indicator_signals[i] = func(signal, **coef_dict["moment"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")

        return self.signal_rule(fast_indicator_signals, slow_indicator_signals, moment_indicator_signals, pre_signals, flag)


    ################################
    def signal_rule(self, fast_indicator_signals, slow_indicator_signals, moment_indicator_signals, pre_signals, flag=True, **kwargs):
        ### 信号规则：
        # SELL: ①slow或fast有80%为-1；②fast和slow有一半为-1；③moment全卖；④fast和moment指标有反转，且1不多
        # BUY: ①slow或fast有80%为1；②fast和slow有一半为1；③moment全买
        # KEEP: 其他情况
        ###
        fast_signal = [0]*3 #分别代表-1,0,1的信号数(快线信号)
        slow_signal = [0]*3 #(慢线信号)
        moment_signal = [0]*3
        for s in fast_indicator_signals:
            fast_signal[int(s)+1] += 1
        for s in slow_indicator_signals:
            slow_signal[int(s)+1] += 1
        for s in moment_indicator_signals:
            moment_signal[int(s)+1] += 1

        # pre_signal: [List, fast_str, moment_str] 分别记录过去10天的信号，总判断 N为消极，P为积极
        neg_fast_inverse_cnt = neg_moment_inverse_cnt = pos_fast_inverse_cnt = pos_moment_inverse_cnt = 0
        for i in range(self.fast_n):
            if flag:
                mean = np.mean(pre_signals[0][i])
                if fast_indicator_signals[i] <= mean-1 or (mean <= -0.5 and fast_indicator_signals[i] <= 0):
                    neg_fast_inverse_cnt += 1
                elif fast_indicator_signals[i]-1 >= mean or (mean >= 0.5 and fast_indicator_signals[i] >= 0):
                    pos_fast_inverse_cnt += 1
                pre_signals[0][i].pop(0)
            pre_signals[0][i].append(fast_indicator_signals[i])
        for j in range(self.moment_n):
            if flag:
                mean = np.mean(pre_signals[0][self.fast_n+j])
                if moment_indicator_signals[j] <= mean-1 or (mean <= -0.5 and moment_indicator_signals[j] <= 0):
                    neg_moment_inverse_cnt += 1
                elif moment_indicator_signals[j]-1 >= mean or (mean >= 0.5 and moment_indicator_signals[j] >= 0):
                    pos_moment_inverse_cnt += 1
                pre_signals[0][self.fast_n+j].pop(0)
            pre_signals[0][self.fast_n+j].append(moment_indicator_signals[j])

        if neg_fast_inverse_cnt >= 0.2*self.fast_n:
            pre_signals[1] = 'N'
        elif pos_fast_inverse_cnt >= 0.2*self.fast_n:
            pre_signals[1] = 'P'
        if neg_moment_inverse_cnt >= 0.2*self.moment_n:
            pre_signals[2] = 'N'
        elif pos_moment_inverse_cnt >= 0.2*self.moment_n:
            pre_signals[2] = 'P'


        fast_cnt = (self.fast_n+1)//2 #评判的阈值为信号数量的一半
        slow_cnt = (self.slow_n+1)//2
        if (fast_signal[0]>=0.8*self.fast_n or slow_signal[0]>=0.8*self.slow_n or \
                (fast_signal[0]>=fast_cnt and slow_signal[0]>=slow_cnt)) or moment_signal[0] == self.moment_n:
            pre_signals[1], pre_signals[2] = 'N', 'N'
            return fast_indicator_signals + slow_indicator_signals + moment_indicator_signals + [pre_signals[1], pre_signals[2], 'SELL']
        elif (fast_signal[2]>=0.8*self.fast_n or slow_signal[2]>=0.8*self.slow_n or \
                (fast_signal[2]>=fast_cnt and slow_signal[2]>=slow_cnt)) or moment_signal[2] == self.moment_n:
            pre_signals[1], pre_signals[2] = 'P', 'P'
            return fast_indicator_signals + slow_indicator_signals + moment_indicator_signals + [pre_signals[1], pre_signals[2], 'BUY']
        elif pre_signals[1] == 'N' and pre_signals[2] == 'N' and (fast_signal[2]+moment_signal[2]) <= 0.2*(self.fast_n+self.moment_n):
            return fast_indicator_signals + slow_indicator_signals + moment_indicator_signals + [pre_signals[1], pre_signals[2], 'SELL']
        else:
            return fast_indicator_signals + slow_indicator_signals + moment_indicator_signals + [pre_signals[1], pre_signals[2], 'KEEP']

    '''
    
    使用normal_current_view版做预测的
    
    '''
    def pred_alarm(self, date, coef_dict, pre_signals, flag=True):
        '''
        Used to get the full quantitative signal
        :date: the signal date
        :coef_dict: the indicator coefficient dictionary
        :pre_signals: record the pre signals, used to calculate today's signal
        :flag: whether consider the pre_signals when calculate today's signal
        :return: SELL, KEEP or BUY
        '''
        try:
            self._update_current_view(date)  # 先更新一下今天的数据视图
        except StopIteration:
            raise StopIteration("Error: date out of data's range")

        ## 更新信号指标实例类使用的数据
        for i in range(self.fast_n):
            self.fast_signal_indicators[i].data = self.normal_current_view
        for i in range(self.slow_n):
            self.slow_signal_indicators[i].data = self.normal_current_view
        for i in range(self.moment_n):
            self.moment_signal_indicators[i].data = self.normal_current_view
        ## 根据参数生成对应信号(短线指标)
        fast_indicator_signals = [0] * self.fast_n
        for i in range(self.fast_n):
            cls_name = type(self.fast_signal_indicators[i]).__name__.lower()  # type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.fast_signal_indicators[i], f'get_{cls_name}')  # 得到信号类_get形式的方法
                signal = func(**coef_dict["fast"][cls_name]["get"])  # 调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.fast_signal_indicators[i], f'{cls_name}_jdg')  # 得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    fast_indicator_signals[i] = func(*signal, **coef_dict["fast"][cls_name][
                        "jdg"])  # 调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    fast_indicator_signals[i] = func(signal, **coef_dict["fast"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")
        ## 根据参数生成对应信号(长线指标)
        slow_indicator_signals = [0] * self.slow_n
        for i in range(self.slow_n):
            cls_name = type(self.slow_signal_indicators[i]).__name__.lower()  # type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.slow_signal_indicators[i], f'get_{cls_name}')  # 得到信号类_get形式的方法
                signal = func(**coef_dict["slow"][cls_name]["get"])  # 调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.slow_signal_indicators[i], f'{cls_name}_jdg')  # 得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    slow_indicator_signals[i] = func(*signal, **coef_dict["slow"][cls_name][
                        "jdg"])  # 调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    slow_indicator_signals[i] = func(signal, **coef_dict["slow"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")
        ## 根据参数生成对应信号(冲量指标)
        moment_indicator_signals = [0] * self.moment_n
        for i in range(self.moment_n):
            cls_name = type(self.moment_signal_indicators[i]).__name__.lower()  # type().__name__获取每个实例信号类的名
            try:
                func = getattr(self.moment_signal_indicators[i], f'get_{cls_name}')  # 得到信号类_get形式的方法
                signal = func(
                    **coef_dict["moment"][cls_name]["get"])  # 调用该_get形式的方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
            except AttributeError:
                raise AttributeError(f"Error: 'get_{cls_name}' method not found!")
            except KeyError:
                raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
            try:
                func = getattr(self.moment_signal_indicators[i], f'{cls_name}_jdg')  # 得到信号类的_jdg形式的方法
                if isinstance(signal, tuple):
                    moment_indicator_signals[i] = func(*signal, **coef_dict["moment"][cls_name][
                        "jdg"])  # 调用该_jdg方法得到最终信号，即由信号数值映射到[-1,0,1]
                else:
                    moment_indicator_signals[i] = func(signal, **coef_dict["moment"][cls_name]["jdg"])
            except AttributeError:
                raise AttributeError(f"Error: Method '{cls_name}_jdg' not found!")

        return self.signal_rule(fast_indicator_signals, slow_indicator_signals, moment_indicator_signals, pre_signals, flag)