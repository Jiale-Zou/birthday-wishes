''' requests只针对HTTP1.1(常规网站)，而小程序一般使用HTTP2 '''

filedNums = list(range(9, -1, -1)) # 场地编号
timeSeries = ['09:30-10:30', '10:30-11:30'] # 时间区间

import datetime
import time
import httpx
import json
import sys

token=  '' #输入微信号token

url = 'https://a.zzsdrgrwhg.com/culturalPalace/culturalPalace/api/whgVenue/goPay'
headers = {
  "x-access-token": token,
  "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c37)XWEB/14185",
  "referer": "https://servicewechat.com/wx96b920c8546e83ba/12/page-frame.html",
}

def doubleGround(datetime, fieldNum, timeSlot, free=True):
    '''
    :param datetime: 要抢几号的场地
    :param fieldNum: 要抢几号场地
    :param free: 是否抢免费场
    :return:
    '''
    totalPrice = str(100 * (1-free)) # 计算总价格

    fields = []
    for x in timeSlot:
        fields.append({"fieldNum":fieldNum,"id":"16552604754251834041","time":x,"price":50,"aboutFlag":1,"employeePrice":None,"sel":1})

    data = {
        "reserveTime":datetime, #"2025-08-01"
        "venueId":"1536900646546984962",
        "items":fields,
        "payType":5,
        "totalPrice":totalPrice,
        "joinNumber":"2"
    }
    # 忽略SSL证书
    client = httpx.Client(verify = False)
    # 发送请求
    resp = client.post(url=url, headers = headers, json = data)
    # 获取数据
    json_data = resp.json()

    return json_data


if __name__ == '__main__':
    timeSlot = sys.argv[1]
    timeSlot = eval(timeSlot)

    dt = (datetime.datetime.now() + datetime.timedelta(days = 1)).strftime("%Y-%m-%d") # 要抢的日期
    # print(f'今天的日期是: {dt}')
    # print('----------------------------->')
    t = datetime.datetime.now().strftime("%H:%M:%S") # 当前时间
    if t < '11:59:40':
        print(json.dumps({
            "success": False,
            "message": "时间太早",
            "detail": "时间太早"
            })
        )
    else:
        while t <= '12:02':
            for x in filedNums:
                resp = doubleGround(dt, x, timeSlot)
                # print(f'当前时间{t}, 抢票结果为: {resp['message']}, 场地为{x}')
                time.sleep(0.05)
                if resp['success']: # 如果抢票成功，终止
                    print(json.dumps({
                          "success": True,
                          "message": "抢票成功",
                          "details": [
                            {
                              "timeSlot": "09:30-10:30",
                              "success": True,
                              "court": f"{x}号场"
                            },
                            {
                              "timeSlot": "10:30-11:30",
                              "success": True,
                              "court": f"{x}号场"
                            }
                          ]
                        })
                    )
                    break
            else:
                t = datetime.datetime.now().strftime("%H:%M") # 更新当前时间
                continue
            break
        else:
            print(json.dumps({
                "success": False,
                "message": "未抢到",
                "detail": "未抢到"
                })
            )


