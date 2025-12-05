from functools import wraps
from contextlib import contextmanager
from time import perf_counter

def time_iter(func):
    """装饰器：迭代多次运行的某个函数，记录总时间"""
    @wraps(func) #使用functools.wraps保留原函数的元信息
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        wrapper.total_time += end_time - start_time
        return result
    wrapper.total_time = 0.0
    return wrapper

def time_deractor(func):
    """装饰器：输出函数运行时间"""
    @wraps(func) #使用functools.wraps保留原函数的元信息
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        print(f'{func.__name__}运行时间: {(end_time-start_time):.4f}s')
        return result
    return wrapper

@contextmanager
def timer(label=''):
    """上下文管理器，记录代码块运行时间"""
    start_time = perf_counter()
    print(label, end=' ')
    try:
        yield #执行with中的语句
    finally:
        end_time = perf_counter()
        print(f'{end_time-start_time:.4f}s')