import numpy as np
import pandas as pd
from datetime import datetime, date

## 解决json序列化格式问题
def default_dump(obj):
    """Convert numpy classes to JSON serializable objects."""
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.values.tolist()
    elif isinstance(obj, (date, datetime)):
        return obj.strftime('%Y-%m-%d')
    else:
        raise TypeError(
            "Unserializable object {} of type {}".format(obj, type(obj))
        )

### 香农模型风险控制 ###
def buy_stock(money, price, init_money, discount_rate, full_posotion = False):
    '''用来定义用money的库存的钱买价格为price的标的'''
    '''香农调整买入，只用初始的3000元; etf要求最少买入100股'''
    if not full_posotion:
        if money*discount_rate > init_money:
            cnt, rem = divmod(init_money*discount_rate, price)
            if cnt < 100:
                return 0,money
            else:
                return cnt, rem+money-init_money
        else:
            cnt, rem = divmod(money*discount_rate, price)
            if cnt < 100:
                return 0,money
            else:
                return cnt, rem
    else:
        cnt, rem = divmod(money*discount_rate, price)
        if cnt < 100:
            return 0,money
        else:
            return cnt, rem