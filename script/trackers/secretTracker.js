// 导入Tracker类，用于埋点
import Tracker from './Tracker.js'

let tracker ;

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
    initTracking();
});

// 发送页面浏览埋点
async function sendPageViewTrack() {
    try {
        const ClientIP = await getClientIP();
        const account = getAccountInfo();

        // 确保endpoint正确
        if (tracker.endpoint.length <= 20) {
            const Domain = await localhostDomain();
            tracker.endpoint = `${Domain}/tracking`;
        }

        await tracker.track({
            account: sha256Hash(account),
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


function initTracking() {
    // 首次初始化：处理现有元素
    setupTracking();
    // 动态监听：处理后续新增元素
    startDOMObservation();
}

// 初始化
let domObserver;

// 当通过innerHTML或appendChild动态添加图片时，MutationObserver会检测到DOM变化，自动重新绑定事件监听器。
// MutationObserver的触发条件：childList 监听子节点增删；subtree 监听所有后代节点（而不仅是直接子节点）；attributes 监听属性变化
function startDOMObservation() {
    domObserver = new MutationObserver(() => setupTracking()); // 当有新节点加入时，重新绑定事件
    domObserver.observe(document.body, {
        childList: true, // 监听子节点变化
        subtree: true, // 监听所有后代节点
    });
}

// 使用事件委托（委托给document）而非直接绑定到元素
function setupTracking() {
    document.removeEventListener('click', trackClickHandler, true); // 移除旧的监听器（避免重复绑定）
    document.addEventListener('click', trackClickHandler, true); // 添加新监听器（true表示在捕获阶段监听，比默认的冒泡阶段更早）
}

// 埋点处理器（避免重复创建函数）//
const trackClickHandler = async (e) => {
    // 1. 找到被点击元素或其父元素中最近的带有data-track属性的元素
    const el = e.target.closest('[data-track]');
    if (!el) return;

    try {
        const ClientIP = await getClientIP();
        const payload = buildTrackPayload(el);
        if ( tracker.endpoint.length <= 20 ) {
            const Domain = await localhostDomain();
            tracker.endpoint = `${Domain}/tracking`;
        }
        tracker.track(payload, ClientIP);
    } catch (error) {
        console.error('埋点处理失败:', error);
    }
};

// 构建埋点数据 //
function buildTrackPayload(el) {
    const extraData = el.getAttribute('data-track-extra');
    return {
        account: sha256Hash(getAccountInfo()),
        page_title: document.title,
        event_type: 'click',        // 事件类型（点击）
        event_name: el.getAttribute('data-track'),   // 获取埋点事件ID
        page_name_lv: getPageHierarchy(),  // 页面路径
        element: el.tagName.toLowerCase(), // 元素标签名（如button/div）
        element_class: el.className, // 元素的class属性
        ...(extraData ? JSON.parse(extraData) : {}), // 展开额外数据
    }
}

// 用于得到当前el的多级页面路径(通过再HTML里设置pageLevel、pageSublevel属性)
function getPageHierarchy(el) {
    const levels = [];
    let current = el;

    while (current && current !== document.body) {
        if (current.dataset.pageLevel) {
            levels.unshift(current.dataset.pageLevel);
        }
        if (current.dataset.pageSublevel) {
            levels.push(current.dataset.pageSublevel);
        }
        current = current.parentElement;
    }

    return levels.join(' > ');
}

// domObserver在页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (domObserver) domObserver.disconnect();
});

