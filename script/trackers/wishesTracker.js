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

    await sendPageViewTrack();
});

// 发送页面浏览埋点
async function sendPageViewTrack() {
    try {
        const ClientIP = await getClientIP();

        // 确保endpoint正确
        if (tracker.endpoint.length <= 20) {
            const Domain = await localhostDomain();
            tracker.endpoint = `${Domain}/tracking`;
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










// 带缓存和错误重试的版本：获取IP地址
const IP_CACHE_KEY = 'client_ip_cache';
async function getClientIP() {
    // 检查session缓存
    const cachedIP = sessionStorage.getItem(IP_CACHE_KEY);
    if (cachedIP) return cachedIP;

    let ip = 'unknown';

    try {
        // 先尝试后端API
        const Domain = await localhostDomain();
        const response = await fetch(`${Domain}/client-ip`, {
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

    // 缓存结果（有效期5分钟）
    sessionStorage.setItem(IP_CACHE_KEY, ip);
    return ip;
}

// 获取Domain
const Domain_CACHE_KEY = 'domain_cache';
async function localhostDomain() {
    // 检查session缓存
    const cachedDomain = sessionStorage.getItem(Domain_CACHE_KEY);
    if (cachedDomain) return cachedDomain;

    let domain = fetch('customize.json')
                .then(response => response.json())
                .then(data => data.localhostDomain);

    // 缓存结果（有效期5分钟）
    sessionStorage.setItem(IP_CACHE_KEY, domain);
    return domain;
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