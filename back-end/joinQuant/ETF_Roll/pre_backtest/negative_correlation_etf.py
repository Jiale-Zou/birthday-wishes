import pandas as pd
import numpy as np
import pymysql

class NegCorr:

    def __init__(self, ip, user, port, pwd):
        self.conn = pymysql.connect(host=ip, user=user, port=port, password=pwd)
        self.cursor = self.conn.cursor()

    def neg_corr_judge(self, date, benchmark, rg):
        ''' 对数据库内的ETF与基准benchmark进行date日前rg天的相关性分析，筛选出负相关性最强的前10只ETF '''
