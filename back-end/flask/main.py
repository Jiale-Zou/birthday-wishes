from flask import Flask, request, jsonify, render_template
import ssl
import re
import json
import requests
import datetime
import subprocess
import atexit
import os
from flask_cors import CORS  # 导入 CORS
from flask_caching import Cache


# 加密算法，用于用户验证
import hashlib
def sha256_hash(message, salt = ''):
    """生成SHA-256哈希"""
    salted_message = message + salt
    return hashlib.sha256(salted_message.encode('utf-8')).hexdigest()
# 账户白名单
valid_accounts = ['19870607908', 'smm']
valid_accounts = {sha256_hash(phone): phone for phone in valid_accounts}
# 清理ANSI转义序列
def clean_ansi_codes(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    return ansi_escape.sub('', text)

'''

日志板块

'''
class LOGS:
    def __init__(self, LOG_FILE, LOG_DIR='./implements/'):
        self.LOG_FILE = LOG_FILE
        self.LOG_DIR = LOG_DIR
        self.log_file_handle = None #全局变量 log_file_handle保持文件打开状态

    def init_logging(self):
        """初始化日志系统"""

        # 确保日志目录存在
        os.makedirs(self.LOG_DIR, exist_ok=True)

        # 打开日志文件（追加模式）
        log_file_path = os.path.join(self.LOG_DIR, self.LOG_FILE)
        self.log_file_handle = open(log_file_path, 'a', encoding='utf-8', buffering=1)  #buffering=1设置行缓冲，确保每条日志即时写入

        # 注册退出时的清理函数（确保程序退出时正确关闭文件）
        atexit.register(self.close_logging)

    def close_logging(self):
        """关闭日志文件"""
        if self.log_file_handle and not self.log_file_handle.closed:
            self.log_file_handle.close()

    def log_request(self, client_ip, client_ua, account, model, request_data):
        """记录请求到日志文件"""
        if not self.log_file_handle or self.log_file_handle.closed:
            self.init_logging()

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} | IP: {client_ip} | ua: {client_ua} | account: {account} | model: {model} | data: {request_data}\n"

        try:
            self.log_file_handle.write(log_entry)
        except IOError as e: #捕获写入异常并尝试恢复
            print(f"日志写入失败: {e}")
            # 尝试重新打开文件
            self.init_logging()
            self.log_file_handle.write(log_entry)



'''

flask框架

'''
app = Flask(__name__)
# 只允许指定的域名访问（替换为你的实际域名）
allowed_origins = [
    "https://jiale-zou.github.io",
]
CORS(app, origins=allowed_origins) # origins=allowed_origins

# @app.route('/')
# def index():
#     return render_template('qwq.html')
# @app.route('/memo.html')
# def secret_html():
#     return render_template('memo.html')

API_KEY = '' # model API
API_URL = 'https://ark.cn-beijing.volces.com/api/v3/images/generations'
@app.route('/picture-diffusion', methods=['POST'])
def picture_diffusion():
    ip = request.headers.get('X-Client-IP')
    ua = request.headers.get('X-User-Agent')
    data = request.get_json()
    account = data.get('account')

    try:
        acc = valid_accounts[account]
    except:
        acc = '错误'

    event_log.log_request(ip, ua, acc, '/picture-diffusion', data)

    if account not in valid_accounts:
        return jsonify({
            'success': False,
            'message': '账户验证失败'
        })

    imgUrl = data.get('imgUrl')
    imgUrl_list = imgUrl.split('/')
    imgUrl = f'https://raw.kkgithub.com/Jiale-Zou/birthday-wishes/refs/heads/master/album/{imgUrl_list[-2]}/{imgUrl_list[-1].split(".")[0]}.png'
    style = data.get('style')
    deviation = data.get('deviation')
    customPrompt = data.get('customPrompt').strip().strip('.,。!?？！、][【】，,;：”’') # 自定义描述

    if customPrompt:
        prompt = f"请在参考图的基础上创作，将其风格变为{style}画风，生成的图片相较参考图的内容元素可以{deviation}偏离。除此之外，优先满足我的如下要求：{customPrompt}。"
    else:
        prompt = f"请在参考图的基础上创作，将其风格变为{style}画风，生成的图片相较参考图的内容元素可以{deviation}偏离。"

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = json.dumps({
        'model': 'doubao-seedream-4-0-250828',
        'prompt': prompt,
        'image': imgUrl,
        'size': '2k',
        'watermark': False
    })

    response = requests.post(API_URL, headers=headers, data=payload)

    if response.status_code == 200:
        response_json = response.json()
        try:
            url = response_json['data'][0]['url']
        except:
            return jsonify({'outUrl': '生成失败'}), 500
        else:
            return jsonify({
                'success': True,
                'message': '请求成功',
                'outUrl': url
            })
    else:
        return jsonify({
            'success': False,
            'message': '接口不可用'
        })



@app.route('/quant')
def quant():
    ip = request.headers.get('X-Client-IP')
    ua = request.headers.get('X-User-Agent')
    account = request.headers.get('X-Account')

    try:
        acc = valid_accounts[account]
    except:
        acc = '错误'

    event_log.log_request(ip, ua, acc, '/quant', None)

    if account not in valid_accounts:
        return jsonify({
            'success': False,
            'message': '账户验证失败。'
        })
    if datetime.datetime.now().strftime('%H:%M:%S') >= '20:00:20': # 数据更新脚本每天20:00更新
        tomorrow = (datetime.date.today() + datetime.timedelta(days=0)).strftime('%Y%m%d')
    else:
        tomorrow = (datetime.date.today() + datetime.timedelta(days=-1)).strftime('%Y%m%d')
    this_year_start = datetime.date.today().strftime('%Y') + '0101'

    # 先看看今天算过没，算过了就加载算过的
    tomorrow_path = f'./implements/quant_res/{tomorrow}.json'
    is_calculated = os.path.exists(tomorrow_path)
    if is_calculated:
        return jsonify({
            "success": True,
            "message": "运行成功",
            "output": json.load(open(tomorrow_path, 'r'))
        })

    quant_script = 'D:\PPrograms\Python\JoinQuant策略\ETF_Roll\singleBacktestForHTML.py'
    python_path = 'D:\PPrograms\Python\JoinQuant策略\.venv\Scripts\python.exe'

    # 执行脚本并捕获所有输出
    result = subprocess.run(
        [python_path, quant_script, this_year_start, tomorrow],
        capture_output=True,  # 捕获 stdout 和 stderr
        text=True,  # 返回字符串（Python 3.7+）
        encoding="utf-8", # cmd默认用gbk编码，而python3用utf-8
    )
    if not is_calculated:
        f = open(tomorrow_path, 'w')
        f.write(result.stdout)
        f.close()

    if result.returncode == 0:
        output = json.loads(result.stdout)  # 解析JSON
        return jsonify({
            "success": True,
            "message": "运行成功",
            "output": output
        })
    else:
        return jsonify({
            "success": False,
            "message": "策略运行失败。"
        })


@app.route('/grab-tickets', methods=['POST'])
def grab_tickets():
    ip = request.headers.get('X-Client-IP')
    ua = request.headers.get('X-User-Agent')
    data = request.get_json()
    account = data.get('account')

    try:
        acc = valid_accounts[account]
    except:
        acc = '错误'

    event_log.log_request(ip, ua, acc, '/grab-tickets', data)

    if account not in valid_accounts:
        return jsonify({
            'success': False,
            'message': '账户验证失败'
        })

    timeSlots = str(data.get('timeSlots'))

    spyder_script = 'D:\PPrograms\Python\爬虫\爬虫project\微信小程序\文化宫抢场地.py'
    python_path = 'D:\PPrograms\Python\爬虫\.venv\Scripts\python.exe'

    result = subprocess.run(
        [python_path, spyder_script, timeSlots],
        capture_output=True,  # 捕获 stdout 和 stderr
        text=True,  # 返回字符串（Python 3.7+）
        encoding="utf-8",  # cmd默认用gbk编码，而python3用utf-8
    )

    if result.returncode == 0:
        output = json.loads(result.stdout)  # 解析JSON
        return jsonify({
            'success': True,
            'message': '运行成功',
            'output': output
        })
    else:
        return jsonify({
            'success': False,
            'message': '运行失败'
        }), 500


@app.route('/ai-chat', methods=['POST'])
def shipu_ai():
    ip = request.headers.get('X-Client-IP')
    ua = request.headers.get('X-User-Agent')
    data = request.get_json()
    account = data.get('account')

    try:
        acc = valid_accounts[account]
    except:
        acc = '错误'
    event_log.log_request(ip, ua, acc, '/ai-chat', data)

    if account not in valid_accounts:
        return jsonify({
            'success': False,
            'message': '账户验证失败'
        })

    message = data.get('message')
    history_raw = data.get('history')
    history = []
    for item in history_raw:
        history.append(f"[usr:<{item['usr_content']}>, ass:<{item['ass_content']}>]")
    history = '\n'.join(history)

    python_path = r'D:\PPrograms\Python\Model Finetune\Langchain\.venv\Scripts\python.exe'
    shipu_script = r'D:\PPrograms\Python\Model Finetune\Langchain\Programs\Website ShiPu\RAGForHTML.py'

    result = subprocess.run([python_path, shipu_script, message, history],
            capture_output = True,  # 捕获 stdout 和 stderr
            text = True,  # 返回字符串（Python 3.7+）
            encoding = "utf-8",  # cmd默认用gbk编码，而python3用utf-8
            )

    if result.returncode == 0:
        output = clean_ansi_codes(result.stdout)
        return jsonify({
            'success': True,
            'message': '运行成功',
            'output': output
        })
    else:
        return jsonify({
            'success': False,
            'message': '运行失败'
        }), 500


'''

IP板块

'''
## 获取IP原理:
## 当客户端（浏览器）访问服务器时，HTTP请求会携带以下关键头部信息
## X-Forwarded-For: 经过代理时追加的客户端IP链
## X-Real-IP: 代理服务器设置的真实客户端IP
## Remote_Addr: 直接与服务器建立连接的IP
## 公共IP的API原理:
## 这些API服务器会检查TCP连接的源IP，在Nginx中对应的变量是$remote_addr
## 由于依赖第三方，可靠性和稳定性不高
def validate_ip(ip):
    """验证IP地址格式"""
    ipv4_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    return re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip)

# 前端调用，尝试第一次获取IP
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
@app.route('/client-ip', methods=['GET'])
@cache.cached(timeout=300)  # 缓存5分钟
def get_client_ip_enhanced():
    try:
        # 获取IP的多种方式（按优先级）
        potential_ips = [
            request.headers.get('X-Real-IP'),
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip(),
            request.remote_addr
        ]

        # 获取第一个有效的IP
        client_ip = next((ip for ip in potential_ips if ip and validate_ip(ip)), 'unknown')

        return jsonify({
            'success': True,
            'ip': client_ip,
            'is_valid': client_ip != 'unknown',
            'request_headers': dict(request.headers)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



'''

埋点板块

'''
@app.route('/tracking', methods=['POST'])
def tracker():
    # 1. 内容类型验证
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    # 2. 数据大小限制（防止DoS攻击）
    if request.content_length > 1024 * 10:  # 10KB

        return jsonify({'error': 'Payload too large'}), 413

    data = request.get_json()
    # 3. 更严格的数据验证
    if not validate_tracking_data(data):
        return jsonify({'error': 'Invalid tracking data'}), 400

    ip = request.headers.get('X-Client-IP')
    ua = request.headers.get('X-User-Agent')
    # 4. 处理每个事件
    for event in data['events']:
        print(event)
        # 验证必需字段
        if not all(k in event for k in ['event_name', 'event_type', 'timestamp']):
            continue

        # 标准化事件数据
        processed = {
            'page_title': event['page_title'],
            'event_name': event['event_name'],
            'event_type': event['event_type'],
            'page_url': event.get('page_url'),
            'page_name_lv': event.get('page_name_lv'),
            'element_class': event.get('element_class'),
            'client_timestamp': datetime.datetime.fromtimestamp(event['timestamp'] / 1000),
            'server_timestamp': datetime.datetime.now(),
            'user_agent': event.get('user_agent'),
        }
        track_log.log_request(ip, ua, event['account'], '/tracking', processed)

    return jsonify({'success': True, 'processed': len(data['events'])})

# 验证网页返回的埋点数据是否合规
def validate_tracking_data(data):
    """验证数据格式"""
    if not isinstance(data, dict): # 是一个dict
        return False
    if 'events' not in data: # 有数据
        return False
    if not isinstance(data['events'], list): # 字典里是一个list
        return False
    if len(data['events']) > 50:  # 限制单次批量大小
        return False

    # 验证每个事件
    for event in data['events']:
        if not isinstance(event, dict): # list里每条记录也是一个dict
            return False
        if not re.match(r'^[a-z0-9_\-]+$', event.get('event_name', '')):
            return False
        if not isinstance(event.get('timestamp'), (int, float)):
            return False

    return True

# 初始化日志系统
event_log = LOGS('request_logs.txt')
track_log = LOGS('track_logs.txt')
event_log.init_logging()
track_log.init_logging()
if __name__ == '__main__':
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("server.cert", "server.key") # ssl自签名证书，开启https服务
        app.run(host='localhost', port=8080, debug=True, ssl_context=context)
    finally:
        event_log.close_logging()
        track_log.close_logging()

