import pandas as pd
import numpy as np
from scipy.optimize import minimize

from ETF_Roll.pre_backtest.indicator import ProductFactory

class Target:
    def __init__(self, index_data_loaders, slow_indicators, minimum_rank_range=100):
        self._index_data_loaders = index_data_loaders # dict: LazyDataLoader
        self.current_view = {key: None for key in index_data_loaders} #一个dict，记录当前各个标的的数据视图，即每次只更新数据视图，而不使用底层数据
        self.normal_current_view = {key: None for key in index_data_loaders} # current_view包含k-1天，而这里包好k天
        self.slow_indicators = [ProductFactory.create_product(s, data=None) for s in slow_indicators] #只使用长线指标
        self.res = pd.DataFrame(columns=[s.lower() for s in slow_indicators], index=list(index_data_loaders.keys())) #用于储存ranks函数结果

        self.minimum_rank_range = minimum_rank_range # 凸优化用到的数据区间的长度
        self.rank_to_be_maximum_ls = np.zeros((minimum_rank_range,len(slow_indicators)), dtype=int) # 每天收益第一名标的的指标排名

        self.weight = None # 计算最优标的的slow_indicator的权重（由minimum_ranking_track_method得到）

    def _update_current_view(self, date):
        '''
        Update the self.current_view according to the date
        :param date: the end date you want to end before
        :return:
        '''
        for tgt in self.current_view:
            try:
                if self.current_view[tgt] is None: # 初始化时，先加载到初始日期的数据块
                    self._index_data_loaders[tgt]._load_chunk_to_date(date)
                elif self._index_data_loaders[tgt].preloaded_data.index[-1] < date:  # 若要使用的日期大于当前加载的数据，则再加载一个数据块
                    self._index_data_loaders[tgt]._load_next_chunk()
            except StopIteration:
                raise StopIteration("Error: date out of data's range")
            self.normal_current_view[tgt] = self._index_data_loaders[tgt].preloaded_data.loc[:date]
            self.current_view[tgt] = self.normal_current_view[tgt].iloc[:-1] # 根据日期更新视图（loc比iloc更快）（loc是闭区间，iloc是开区间）

    def minimum_ranking_track_method(self, date, coef_dict):
        '''
        use minimum ranking tracking method to get the weight of indicator when rank the index in index pool
        :param date: the end date you want to end before
        :param coef_dict: the indicator coefficient dictionary
        :return:
        '''
        ## 一、要使用minimum ranking tracking，先要有self.minimum_rank_range长度的前置数据 ##
        if self.rank_to_be_maximum_ls[0][0] == 0:
            # 1.对过去self.minimum_rank_rang天
            for i in range(-self.minimum_rank_range, 0):
                try:
                    self._update_current_view(date)  # 由于后面rank会覆盖数据视图，因此每次都要先更新一下今天的数据视图
                except StopIteration:
                    raise StopIteration("Error: date out of data's range")
                # 2.找到当天最大涨跌幅的标的
                max_return = -float('inf') #当前最大收益
                max_target = None #当前最大收益的标的
                for tgt in self.current_view:
                    yld = self.current_view[tgt].iloc[i]['涨跌幅'] #注意前面的self._update_current_view(date)是更新到date昨天的数据，则这里是计算昨天
                    if yld > max_return:
                        max_return = yld
                        max_target = tgt
                # 3.计算该标的当天的slow_rank（对于T天的最优标的，计算其指标排名使用的是T-1天的数据）
                pre_date = self.current_view[tgt].index[i-1] #找到前一天的日期
                self.ranks(pre_date, coef_dict) #计算指标排名
                max_target_ranks = self.res.loc[max_target] #得到该max_target的指标排名
                self.rank_to_be_maximum_ls[i] = self.rank_to_be_maximum_ls[i]+max_target_ranks #更新前缀列表
        else: ## 之前已近计算过一部分前缀了，可以利用
            try:
                self._update_current_view(date)  # 先更新一下今天的数据视图
            except StopIteration:
                raise StopIteration("Error: date out of data's range")
            # 1.找到昨天的最优标的
            max_return = -float('inf')  # 当前最大收益
            max_target = None  # 当前最大收益的标的
            for tgt in self.current_view:
                yld = self.current_view[tgt].iloc[-1]['涨跌幅']  # 注意前面的self._update_current_view(date)是更新到date昨天的数据，则这里是计算昨天
                if yld > max_return:
                    max_return = yld
                    max_target = tgt
            # 2.利用截至前天的数据计算昨天的指标排名
            pre_date = self.current_view[tgt].index[-2]  # 找到前一天的日期
            self.ranks(pre_date, coef_dict)  # 计算指标排名
            max_target_ranks = self.res.loc[max_target]  # 得到该max_target的指标排名
            self.rank_to_be_maximum_ls = np.concatenate((np.expand_dims(max_target_ranks,axis=0),self.rank_to_be_maximum_ls[:-1]), axis=0)  # 更新前缀列表

        ## 二、利用minimum ranking tracking计算指标权总（KKT条件） ##
        def objective(x, coef):
            return np.sum(np.square(np.dot(coef, x)))
        def constraint(x):
            return np.sum(x) - 1
        # 初始点
        x0 = np.zeros(len(self.slow_indicators), dtype=float)
        # 边界条件
        bounds = [(0, 0.4) for _ in range(len(x0))]
        # 约束
        cons = [
            {'type': 'eq', 'fun': constraint}
        ]
        # 求解
        solution = minimize(objective, x0, method='SLSQP', constraints=cons, bounds=bounds, args=self.rank_to_be_maximum_ls)
        self.weight = solution.x

        pass


    def ranks(self, date, coef_dict):
        '''
        get a dataframe（self.res） show the ranks of indexes in index pool
        :param date: the indicator date
        :param coef_dict: the indicator coefficient dictionary
        :return: a dataframe, the index is the index'code、the column is the indicator and the data is the rank
        '''
        try:
            self._update_current_view(date) # 先更新一下今天的数据视图
        except StopIteration:
            raise StopIteration("Error: date out of data's range")
        # 对于每个index，计算对应slow_indicators的得分
        for tgt in self.current_view:
            # 计算当前标的的各个指标的得分
            for i in range(len(self.slow_indicators)):
                self.slow_indicators[i].data = self.current_view[tgt] #更新得分计算器到当前的标的数据视图
                cls_name = type(self.slow_indicators[i]).__name__.lower() #得到指标的名称
                try:
                    func = getattr(self.slow_indicators[i], 'slow_rank_score')  # 得到信号类slow_rank_score的方法
                    score = func(**coef_dict["slow"][cls_name]["get"])  # 调用该slow_rank_score方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
                except AttributeError:
                    raise AttributeError(f"Error: Class {cls_name} has no 'slow_rank_score' method!")
                except KeyError:
                    raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
                self.res.loc[tgt, cls_name] = score # 记录tgt标的cls_name指标的得分
        # 计算各标的对应指标的排名
        for col in self.res.columns:
            self.res[col] = self.res[col].rank(method='min', ascending=False)


    def get_best_target(self, date, coef_dict):
        '''
        Used to get today's best target (according to comprehensive indicators' rank)
        :param date: the indicator date
        :param coef_dict: the indicator coefficient dictionary
        :return: the target in index pool (for example: '上证180ETF')
        '''
        self.minimum_ranking_track_method(date, coef_dict) # 得到指标权重
        self.ranks(date, coef_dict) # 得到各标的指标排名
        comprehensive_rank = np.dot(self.res, self.weight)
        return self.res.index[np.argmax(comprehensive_rank)]


    '''
    
    下面是使用normal_current_view版做预测的
    
    '''

    def pred_minimum_ranking_track_method(self, date, coef_dict):
        ## 一、要使用minimum ranking tracking，先要有self.minimum_rank_range长度的前置数据 ##
        if self.rank_to_be_maximum_ls[0][0] == 0:
            # 1.对过去self.minimum_rank_rang天
            for i in range(-self.minimum_rank_range, 0):
                try:
                    self._update_current_view(date)  # 由于后面rank会覆盖数据视图，因此每次都要先更新一下今天的数据视图
                except StopIteration:
                    raise StopIteration("Error: date out of data's range")
                # 2.找到当天最大涨跌幅的标的
                max_return = -float('inf')  # 当前最大收益
                max_target = None  # 当前最大收益的标的
                for tgt in self.normal_current_view:
                    yld = self.normal_current_view[tgt].iloc[i]['涨跌幅']  # 注意这里是计算今天
                    if yld > max_return:
                        max_return = yld
                        max_target = tgt
                # 3.计算该标的当天的slow_rank（对于T天的最优标的，计算其指标排名使用的是T-1天的数据）
                pre_date = self.normal_current_view[tgt].index[i - 1]  # 找到前一天的日期
                self.pred_ranks(pre_date, coef_dict)  # 计算指标排名
                max_target_ranks = self.res.loc[max_target]  # 得到该max_target的指标排名
                self.rank_to_be_maximum_ls[i] = self.rank_to_be_maximum_ls[i] + max_target_ranks  # 更新前缀列表
        else:  ## 之前已近计算过一部分前缀了，可以利用
            try:
                self._update_current_view(date)  # 先更新一下今天的数据视图
            except StopIteration:
                raise StopIteration("Error: date out of data's range")
            # 1.找到今天的最优标的
            max_return = -float('inf')  # 当前最大收益
            max_target = None  # 当前最大收益的标的
            for tgt in self.current_view:
                yld = self.normal_current_view[tgt].iloc[-1]['涨跌幅']  # 注意这里是计算今天的
                if yld > max_return:
                    max_return = yld
                    max_target = tgt
            # 2.利用截至昨天的数据计算今天的指标排名
            pre_date = self.normal_current_view[tgt].index[-2]  # 找到昨天的日期
            self.pred_ranks(pre_date, coef_dict)  # 计算指标排名
            max_target_ranks = self.res.loc[max_target]  # 得到该max_target的指标排名
            self.rank_to_be_maximum_ls = np.concatenate(
                (np.expand_dims(max_target_ranks, axis=0), self.rank_to_be_maximum_ls[:-1]), axis=0)  # 更新前缀列表

        ## 二、利用minimum ranking tracking计算指标权总（KKT条件） ##
        def objective(x, coef):
            return np.sum(np.square(np.dot(coef, x)))

        def constraint(x):
            return np.sum(x) - 1

        # 初始点
        x0 = np.zeros(len(self.slow_indicators), dtype=float)
        # 边界条件
        bounds = [(0, 0.4) for _ in range(len(x0))]
        # 约束
        cons = [
            {'type': 'eq', 'fun': constraint}
        ]
        # 求解
        solution = minimize(objective, x0, method='SLSQP', constraints=cons, bounds=bounds,
                            args=self.rank_to_be_maximum_ls)
        self.weight = solution.x

        pass

    def pred_ranks(self, date, coef_dict):
        '''
        get a dataframe（self.res） show the ranks of indexes in index pool
        :param date: the indicator date
        :param coef_dict: the indicator coefficient dictionary
        :return: a dataframe, the index is the index'code、the column is the indicator and the data is the rank
        '''
        try:
            self._update_current_view(date) # 先更新一下今天的数据视图
        except StopIteration:
            raise StopIteration("Error: date out of data's range")
        # 对于每个index，计算对应slow_indicators的得分
        for tgt in self.normal_current_view:
            # 计算当前标的的各个指标的得分
            for i in range(len(self.slow_indicators)):
                self.slow_indicators[i].data = self.normal_current_view[tgt] #更新得分计算器到当前的标的数据视图
                cls_name = type(self.slow_indicators[i]).__name__.lower() #得到指标的名称
                try:
                    func = getattr(self.slow_indicators[i], 'slow_rank_score')  # 得到信号类slow_rank_score的方法
                    score = func(**coef_dict["slow"][cls_name]["get"])  # 调用该slow_rank_score方法，得到信号数值(func已经是方法对象，不需要通过实例类调用了)
                except AttributeError:
                    raise AttributeError(f"Error: Class {cls_name} has no 'slow_rank_score' method!")
                except KeyError:
                    raise KeyError(f"Error: '{cls_name}' key not in coef_dict!")
                self.res.loc[tgt, cls_name] = score # 记录tgt标的cls_name指标的得分
        # 计算各标的对应指标的排名
        for col in self.res.columns:
            self.res[col] = self.res[col].rank(method='min', ascending=False)

    def pred_get_best_target(self, date, coef_dict):
        '''
        Used to get today's best target (according to comprehensive indicators' rank)
        :param date: the indicator date
        :param coef_dict: the indicator coefficient dictionary
        :return: the target in index pool (for example: '上证180ETF')
        '''
        self.pred_minimum_ranking_track_method(date, coef_dict) # 得到指标权重
        self.pred_ranks(date, coef_dict) # 得到各标的指标排名
        comprehensive_rank = np.dot(self.res, self.weight)
        return self.res.index[np.argmax(comprehensive_rank)]


