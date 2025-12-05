import numpy as np

# 这里是用到的技术指标
Signal_Indicator = ['MA','CCI','IDR','ADX','RSRS','BOLL','OBV','MFI','MACD','WPM','AD']
Moment_Indicator = ['BOLL', 'CCI', 'WPM'] #选取当天数据，比较标准选取长时间维度，反映比fast_indicator灵敏，但在振荡行情下会失效
Slow_Indicator = ['RSRS', 'IDR', 'OBV'] #衡量长时间维度的走势
Fast_Indicator = ['MA', 'MACD', 'MFI', 'ADX', 'AD'] #衡量短时间维度的近期走势

# 这里是回测的基准标的
Benchmark = '沪深300'

# 这里是技术指标的参数范围
coef_range = {
    "fast": {
             "ma": {"get": {"N": range(1, 6), "M": range(10, 31, 1)},
                    "jdg": {"criterion": np.arange(1, 1.021, 0.001)}
                    },
             "macd": {"get": {"rt_length": range(7, 15), "fast": range(9, 15), "slow": range(18, 30, 1), "signal": range(7, 15, 1)},
                      "jdg": {"placeholder": None}
                      },
             "mfi": {"get": {"N": range(5, 41)},
                     "jdg": {"threshold": np.arange(40, 81)}
                     },
             "adx": {"get": {"N": range(10, 31)},
                     "jdg": {"threshold": range(30, 90)}
                     },
             "ad": {"get": {"N": range(1, 11), "M": range(10, 41)},
                    "jdg": {"criterion": np.arange(1, 1.031, 0.01)}
                    }
    },
    "slow": {
             "rsrs": {"get": {"N": range(15, 31), "M": range(100, 301, 5)},
                      "jdg": {"threshold": np.arange(0.4, 0.9, 0.1)}
                      },
             "idr": {"get": {"N": range(15, 31), "M": range(150,351, 5)},
                     "jdg": {"threshold": np.arange(0.4, 0.9, 0.1)}
                     },
             "obv": {"get": {"N": range(10, 31), "M": range(200, 351, 10)},
                     "jdg": {"threshold": np.arange(0.7, 1.8, 0.1)}
                     }
    },
    "moment": {
                "cci": {"get": {"window": range(200, 401, 5)},
                        "jdg": {"threshold": range(80, 121)}
                        },
                "boll": {"get": {"window": range(200, 301)},
                         "jdg": {"pct": np.arange(1, 2.1, 0.1)}
                         },
                "wpm": {"get": {"N": range(10, 30), "M": range(200, 301, 10)},
                        "jdg": {"threshold": np.arange(0.1, 0.5, 0.02)}
                        }
    }
}

# indicator参数:从coef_range中参数搜索来的，最终使用的参数
# coef = {
#     "fast": {
#         "ma": {"get": {"N": 3, "M": 25}, "jdg": {"criterion": 1.0169999999999981}},
#         "macd": {"get": {"rt_length": 14, "fast": 9, "slow": 25, "signal": 9}, "jdg": {"placeholder": None}},
#         "mfi": {"get": {"N": 33}, "jdg": {"threshold": 50}},
#         "adx": {"get": {"N": 28}, "jdg": {"threshold": 35}},
#         "ad": {"get": {"N": 4, "M": 24}, "jdg": {"criterion": 1.02}}},
#     "slow": {
#         "rsrs": {"get": {"N": 21, "M": 185}, "jdg": {"threshold": 0.5}},
#         "idr": {"get": {"N": 17, "M": 165}, "jdg": {"threshold": 0.7999999999999999}},
#         "obv": {"get": {"N": 23, "M": 300}, "jdg": {"threshold": 1.0999999999999999}}},
#     "moment": {
#         "cci": {"get": {"window": 345}, "jdg": {"threshold": 94}},
#         "boll": {"get": {"window": 296}, "jdg": {"pct": 1.5000000000000004}},
#         "wpm": {"get": {"N": 23, "M": 260}, "jdg": {"threshold": 0.28}}
#     }
# }
coef = {"fast": {"ma": {"get": {"N": 2, "M": 28}, "jdg": {"criterion": 1.0079999999999991}}, "macd": {"get": {"rt_length": 10, "fast": 12, "slow": 27, "signal": 14}, "jdg": {"placeholder": None}}, "mfi": {"get": {"N": 19}, "jdg": {"threshold": 71}}, "adx": {"get": {"N": 10}, "jdg": {"threshold": 66}}, "ad": {"get": {"N": 9, "M": 15}, "jdg": {"criterion": 1.0}}}, "slow": {"rsrs": {"get": {"N": 17, "M": 105}, "jdg": {"threshold": 0.5}}, "idr": {"get": {"N": 22, "M": 315}, "jdg": {"threshold": 0.6}}, "obv": {"get": {"N": 16, "M": 330}, "jdg": {"threshold": 0.9999999999999999}}}, "moment": {"cci": {"get": {"window": 270}, "jdg": {"threshold": 92}}, "boll": {"get": {"window": 228}, "jdg": {"pct": 1.0}}, "wpm": {"get": {"N": 13, "M": 250}, "jdg": {"threshold": 0.16000000000000003}}}}


# 这里表示参数优化是是否使用Redis分布式
IF_DISTRIBUTED = False

# 训练模型的时间区间
start_date = '2020-01-01'
end_date = '2024-12-31'

# 指标分组标准：长线指标、短线指标、瞬时指标
# 股票池分类：长期相关性高的标的
# 买卖评判：只要是买入，就买slow表现最好的标的