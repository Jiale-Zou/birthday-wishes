export default class Tracker {
    // 构造函数：初始化配置
    constructor(options = {}) {
        // 后端接收埋点数据的API地址
        this.endpoint = options.endpoint || '/tracking';

        // 应用标识，区分不同项目
        this.appId = options.appId;

        // SDK版本，用于后续数据兼容
        this.version = options.version || '1.0.0';

        // 环境标识：development/test/production
        this.environment = options.env || 'production';

        // 待发送的数据队列
        this.queue = [];

        // 防止重复发送的锁
        this.isSending = false;
    }

    // 核心方法：记录埋点数据
    track(eventData, ClientIP) {
        // 基础数据（自动采集）
        const baseData = {
            app_id: this.appId,         // 应用ID
            version: this.version,     // 版本号
            env: this.environment,     // 环境
            timestamp: Date.now(),     // 时间戳
            page_url: window.location.href,  // 当前页URL
            referrer: document.referrer,      // 来源页
            user_agent: navigator.userAgent  // 设备信息
        };

        // 合并基础数据和业务自定义数据
        const mergedData = {...baseData, ...eventData};

        // 加入发送队列
        this.queue.push(mergedData);

        // 尝试发送
        this.sendBatch(ClientIP);
    }

    // 批量发送方法
    sendBatch(ClientIP) {
        // 如果正在发送或队列为空则终止
        if (this.isSending || this.queue.length === 0) return;

        this.isSending = true;  // 加锁

        // 取出前20条（避免一次性发送太多）
        const batch = this.queue.slice(0, 20);

        // 保留剩余数据
        this.queue = this.queue.slice(20);


        // 发送到后端
        fetch(this.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Agent': navigator.userAgent,
                'X-Client-IP': ClientIP,
            },
            body: JSON.stringify({ events: batch })  // 批量数据
        })
        .then(() => {
            this.isSending = false;  // 解锁

            // 如果还有数据，0.5秒后继续发送
            if (this.queue.length > 0) {
                setTimeout(() => this.sendBatch(), 500);
            }
        })
        .catch(() => {
            this.isSending = false;  // 解锁

            // 发送失败，将数据重新放回队列头部
            this.queue = [...batch, ...this.queue];
        });
    }
}