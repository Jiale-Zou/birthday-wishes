// 导入Tracker类，用于埋点
import Tracker from './Tracker.js'

let tracker;

document.addEventListener('DOMContentLoaded', async function() {
    tracker =  new Tracker({
        debug: false,  // 正式环境设为false
        appId: 'Happy_Birthday_web',  // 项目标识
        endpoint: '/tracking',  // 后端接口
        env: window.__ENV__ || 'production'  // 自动区分环境
    });

    // 页面加载时清理无效缓存
    clearInvalidIPCache();
    await sendPageViewTrack();
});

// 获取Domain
async function localhostDomain() {
    let domain = fetch('../static/customize.json')
                .then(response => response.json())
                .then(data => data.localhostDomain);
    return domain;
}
async function proxyDomain() {
    let proxy = fetch('../static/customize.json')
                .then(response => response.json())
                .then(data => data.proxyDomain);
    return proxy;
}

async function getBothDomains() {
    try {
        // 关键步骤：使用 Promise.all 并行执行两个异步函数
        const [localhost, proxy] = await Promise.all([
            localhostDomain(),
            proxyDomain()
        ]);

        // 此时，localhost 变量包含 localhostDomain 的返回值
        // proxy 变量包含 proxyDomain 的返回值
        console.log('Localhost Domain:', localhost);
        console.log('Proxy Domain:', proxy);

        // 返回一个对象，方便在函数外部使用
        return {
            localhostDomain: localhost,
            proxyDomain: encodeURIComponent(proxy)
        };

    } catch (error) {
        // 统一错误处理：如果任何一个异步函数失败，都会在这里捕获
        console.error('Failed to fetch one or more domains:', error);
        throw error; // 可以选择重新抛出错误，或者返回默认值
    }
}

// 发送页面浏览埋点
async function sendPageViewTrack() {
    try {
        const ClientIP = await getClientIP();

        // 确保endpoint正确
        if (tracker.endpoint.length <= 20) {
            const Domain = await getBothDomains();
            tracker.endpoint = `${Domain.proxyDomain}${Domain.localhostDomain}/tracking`;
        }

        await tracker.track({
            account: '',
            page_title: document.title,
            event_type: 'page_view',
            event_name: 'page_load',
            page_name_lv: '',
            page_url: window.location.href,
        }, ClientIP);

        console.log('页面浏览埋点发送成功');
    } catch (error) {
        console.error('页面浏览埋点失败:', error);
    }
}

// 清理无效的IP缓存
function clearInvalidIPCache() {
    const cachedIP = sessionStorage.getItem(IP_CACHE_KEY);
    if (cachedIP && !isValidIP(cachedIP)) {
        console.log('清理无效IP缓存:', cachedIP);
        sessionStorage.removeItem(IP_CACHE_KEY);
    }
}








// 带缓存和错误重试的版本：获取IP地址(但由于：异步操作未完成时进行缓存，或错误地缓存了Promise对象)
const IP_CACHE_KEY = 'client_ip_cache';
async function getClientIP() {
    // 检查session缓存
    const cachedIP = sessionStorage.getItem(IP_CACHE_KEY);
    // 验证缓存值是否为有效IP
    if (cachedIP && isValidIP(cachedIP)) {
        return cachedIP;
    }

    let ip = 'unknown';

    try {
        // 先尝试后端API
        const Domain = await getBothDomains();
        const response = await fetch(`${Domain.proxyDomain}${Domain.localhostDomain}/client-ip`, {
            headers: {
                'Cache-Control': 'no-cache',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();
        if (data.ip && data.ip !== 'unknown') {
            ip = data.ip;
        } else {
            // 后端获取失败时尝试公共API
            ip = await fetchPublicIP();
        }
    } catch (error) {
        console.error('获取IP失败:', error);
        ip = await fetchPublicIP();
    }

    // 验证IP格式后再缓存
    if (isValidIP(ip)) {
        sessionStorage.setItem(IP_CACHE_KEY, ip);
    } else {
        sessionStorage.removeItem(IP_CACHE_KEY); // 清除无效缓存
    }
    return ip;
}

// 新增：IP格式验证函数
function isValidIP(ip) {
    if (!ip || ip === 'unknown') return false;
    if (ip.includes('Promise') || ip.includes('object')) return false; // 排除Promise对象
    if (ip.includes('[') || ip.includes(']')) return false; // 排除数组表示

    // 基本IP格式验证（IPv4或IPv6）
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;

    return ipv4Regex.test(ip) || ipv6Regex.test(ip) || ip === 'unknown';
}


// 使用公共API获取客户端IP地址（异步）
async function fetchPublicIP() {
    const services = [
        'https://api.ipify.org?format=json',
        'https://ipapi.co/json/',
        'https://ipinfo.io/json',
        'https://api.myip.com',
        'https://worldtimeapi.org/api/ip'
    ];

    for (const url of services) {
        try {
            const response = await fetch(url, {
                headers: { 'Accept': 'application/json' }
            });
            const data = await response.json();
            return data.ip || data.ipAddress || 'unknown';
        } catch (e) {
            console.log(`尝试 ${url} 失败`, e);
        }
    }
    return 'unknown';
}