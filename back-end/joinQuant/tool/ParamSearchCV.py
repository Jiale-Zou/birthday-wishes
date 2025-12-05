import random
from collections.abc import Iterable

def is_iterrable_not_string(obj):
    """检查是否为可迭代对象（排除字符串）"""
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))

def recursive_random_select_param(original_dict):
    """递归实现字典结构拷贝；仅复制字典的嵌套结构，最内层的为可迭代对象时，随机选择一个数"""
    if isinstance(original_dict, dict): # 还是字典，继续递归
        return {key: recursive_random_select_param(value) for key, value in original_dict.items()}
    elif is_iterrable_not_string(original_dict): #是可迭代对象，随机选一个数
        return random.choice(original_dict)
    else: # 是固定值，返回原值
        return original_dict

def RandomSearchCV(dic_Range, n_iter):
    """随机参数生成"""
    ## 等概率随机采样得到参数组合
    return [recursive_random_select_param(dic_Range) for _ in range(n_iter)]

