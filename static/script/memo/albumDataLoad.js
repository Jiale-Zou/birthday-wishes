// 加密算法
function sha256Hash(message, salt = '') {
  const saltedMessage = message + salt;
  return CryptoJS.SHA256(saltedMessage).toString(CryptoJS.enc.Hex);
}


// 全局状态管理
const appState = {
    isMusicPlaying: false,
    allImages: [],
    currentImageIndex: 0,
    currentTab: 'home',
    account: '',
    showAccount: false,
};


// 主初始化函数
document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initMusicPlayer();
    initPhotoAlbum();
    initDiffusion();
    loadStrategyPerformance();
    initTicketGrab();
    initAccountInput();
    initAIChat();
});


// 账户输入框初始化函数
function initAccountInput() {
    const accountInput = document.getElementById('account-input');
    const toggleBtn = document.querySelector('.toggle-visibility');
    const eyeIcon = document.querySelector('.eye-icon');

    // 从本地存储恢复账户信息
    const savedAccount = localStorage.getItem('userAccount');
    if (savedAccount) {
        accountInput.value = savedAccount;
        appState.account = savedAccount;
    }

    // 监听输入变化并保存
    accountInput.addEventListener('input', function() {
        appState.account = this.value;
        localStorage.setItem('userAccount', this.value);

        // 如果是密码模式，显示星号
        if (accountInput.type === 'password') {
            this.value = '*'.repeat(appState.account.length);
        }
    });

    // 切换显示/隐藏
    toggleBtn.addEventListener('click', function() {
        appState.showAccount = !appState.showAccount;

        if (appState.showAccount) {
            // 显示真实账号
            accountInput.type = 'text';
            accountInput.value = appState.account;
            eyeIcon.classList.remove('fa-eye-slash');
            eyeIcon.classList.add('fa-eye');
            eyeIcon.style.color = '#4a89dc';
        } else {
            // 显示星号
            accountInput.type = 'password';
            accountInput.value = '*'.repeat(appState.account.length);
            eyeIcon.classList.remove('fa-eye');
            eyeIcon.classList.add('fa-eye-slash');
            eyeIcon.style.color = '#7f8c8d';
        }
    });

    // 防止点击按钮时输入框失去焦点
    toggleBtn.addEventListener('mousedown', function(e) {
        e.preventDefault();
    });

    // 确保输入框不会被Tab切换重置
    document.addEventListener('visibilitychange', function() {
        if (accountInput.value !== appState.account) {
            accountInput.value = appState.account;
        }
    });
}

// Tab切换功能
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // 更新当前标签状态
            appState.currentTab = this.getAttribute('data-tab');

            // 更新UI
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            this.classList.add('active');
            document.getElementById(appState.currentTab).classList.add('active');

            // 按需加载数据
            if (appState.currentTab === 'stocks') {
                loadStrategyPerformance();
            }
            // 可以添加抢票页面的初始化逻辑
        });

        // 默认激活首页
        if (button.getAttribute('data-tab') === 'home') {
            button.classList.add('active');
            document.getElementById('home').classList.add('active');
        }
    });
}

// 音乐播放器功能
function initMusicPlayer() {
    const musicPlayer = document.getElementById('music-player');
    const bgMusic = document.getElementById('bg-music');
    const musicSelector = document.getElementById('music-selector');

    // 当前播放的音乐
    let currentMusic = bgMusic.src;

    // 点击播放/暂停
    musicPlayer.addEventListener('click', function() {
        if (appState.isMusicPlaying) {
            bgMusic.pause();
            musicPlayer.classList.remove('playing');
        } else {
            bgMusic.play()
                .then(() => {
                    musicPlayer.classList.add('playing');
                })
                .catch(error => {
                    console.error('自动播放被阻止:', error);
                    musicPlayer.textContent = '点击播放音乐';
                });
        }
        appState.isMusicPlaying = !appState.isMusicPlaying;
    });

    // 切换音乐（修改部分）
    musicSelector.addEventListener('change', function() {
        const newSource = this.value;
        if (newSource !== currentMusic) {
            // 保存当前播放状态
            const wasPlaying = appState.isMusicPlaying;

            // 切换音乐源并重置播放位置
            bgMusic.volume = 0.5; // 初始音量
            bgMusic.pause();
            bgMusic.src = newSource;
            bgMusic.currentTime = 0; // 关键修改：强制从头开始
            currentMusic = newSource;

            // 恢复播放状态(淡入播放的模式)
            if (wasPlaying) {
                bgMusic.volume = 0;
                bgMusic.play()
                    .then(() => {
                        musicPlayer.classList.add('playing');
                    })
                    .catch(error => {
                        console.error('音乐切换后自动播放失败:', error);
                        musicPlayer.classList.remove('playing');
                        appState.isMusicPlaying = false;
                    });
                const fadeIn = setInterval(() => {
                    if (bgMusic.volume < 0.5) {
                        bgMusic.volume += 0.05;
                    } else {
                        clearInterval(fadeIn);
                    }
                }, 100);
            }
        }
    });

    // 用户第一次交互后尝试自动播放
    document.body.addEventListener('click', function initMusic() {
        if (!appState.isMusicPlaying) {
            bgMusic.play()
                .then(() => {
                    musicPlayer.classList.add('playing');
                    appState.isMusicPlaying = true;
                })
                .catch(console.log);
        }
        document.body.removeEventListener('click', initMusic);
    }, { once: true });
}

// 照片墙功能
function initPhotoAlbum() {
    const galleries = [
        { id: 'kongfu-gallery', prefix: 'kongfu', count: 27 },
        { id: 'jeju-gallery', prefix: 'jeju', count: 51 },
        { id: 'else-gallery', prefix: 'else', count: 5 }
    ];

    galleries.forEach(gallery => {
        const container = document.getElementById(gallery.id);
        for (let i = 1; i <= gallery.count; i++) {
            const itemIndex = appState.allImages.length;
            const alt = `${gallery.prefix}${i}`;
            const src = `../static/album/${gallery.prefix}/${i}.jpg`;

            appState.allImages.push({ src, alt });

            container.innerHTML += `
                <div class="gallery-item" data-index="${itemIndex}" data-page-level="photo-album" data-page-sublevel="${gallery.prefix}">
                    <img src="${src}" alt="${alt}" loading="lazy" data-track="gallery_image_click" data-track-extra='{"alt": "${alt}"}'>
                    <div class="image-caption">${alt}</div>
                </div>
            `;
        }
    });

    initLightbox();
    initMobileGestures();
}

// 移动端手势支持
function initMobileGestures() {
    let touchTimer = null;

    document.addEventListener('touchstart', function(e) {
        const galleryItem = e.target.closest('.gallery-item');
        if (galleryItem) {
            touchTimer = setTimeout(() => {
                galleryItem.classList.add('show-caption');
                touchTimer = null;
            }, 500);
        }
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        if (touchTimer) clearTimeout(touchTimer);
        const galleryItem = e.target.closest('.gallery-item');
        if (galleryItem) galleryItem.classList.remove('show-caption');
    }, { passive: true });
}

// Lightbox功能
function initLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxContent = document.getElementById('lightbox-content');
    const lightboxClose = document.getElementById('lightbox-close');
    const lightboxPrev = document.getElementById('lightbox-prev');
    const lightboxNext = document.getElementById('lightbox-next');

    // 点击图片打开lightbox
    document.addEventListener('click', function(e) {
        const imgElement = e.target.closest('.gallery-item img');
        if (imgElement) {
            // 新增：检查是否应该跳过埋点
            if (e.target.closest('[data-no-track]')) return;

            const galleryItem = imgElement.closest('.gallery-item');
            const index = parseInt(galleryItem?.getAttribute('data-index'));
            if (!isNaN(index)) {
                appState.currentImageIndex = index;
                openLightbox();
            }
        }
    });

    // Lightbox操作
    function openLightbox() {
        const image = appState.allImages[appState.currentImageIndex];
        lightboxContent.innerHTML = `<img src="${image.src}" alt="${image.alt}">`;
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        lightbox.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    function prevImage() {
        appState.currentImageIndex = (appState.currentImageIndex - 1 + appState.allImages.length) % appState.allImages.length;
        openLightbox();
    }

    function nextImage() {
        appState.currentImageIndex = (appState.currentImageIndex + 1) % appState.allImages.length;
        openLightbox();
    }

    // 绑定事件
    lightboxClose.addEventListener('click', closeLightbox);
    lightboxPrev.addEventListener('click', prevImage);
    lightboxNext.addEventListener('click', nextImage);

    // 键盘控制
    document.addEventListener('keydown', function(e) {
        if (lightbox.style.display === 'flex') {
            if (e.key === 'Escape') closeLightbox();
            else if (e.key === 'ArrowLeft') prevImage();
            else if (e.key === 'ArrowRight') nextImage();
        }
    });

    // 点击背景关闭
    lightbox.addEventListener('click', function(e) {
        if (e.target === lightbox) closeLightbox();
    });
}


// 获取账户信息
function getAccountInfo() {
    const accountInput = document.getElementById('account-input');
    return accountInput.value.trim(); // 返回去除前后空格的账户名
}

// 带缓存和错误重试的版本：获取IP地址
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

    // 新增：验证IP格式后再缓存
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

// 清理无效的IP缓存
function clearInvalidIPCache() {
    const cachedIP = sessionStorage.getItem(IP_CACHE_KEY);
    if (cachedIP && !isValidIP(cachedIP)) {
        console.log('清理无效IP缓存:', cachedIP);
        sessionStorage.removeItem(IP_CACHE_KEY);
    }
}

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

// Diffusion功能
function initDiffusion() {
    const sourceImageInput = document.getElementById('source-image-input');
    const sourceImageOptions = document.getElementById('source-image-options');
    const styleInput = document.getElementById('style-input');
    const generateBtn = document.getElementById('generate-btn');
    const generatedImage = document.getElementById('generated-image');
    const placeholderText = document.getElementById('placeholder-text');
    const loadingSpinner = document.getElementById('loading-spinner');
    const sourceImageSelect = document.getElementById('source-image-select');


    // 填充源图片选择框
    function populateSourceImages() {
        sourceImageOptions.innerHTML = '';
        document.querySelectorAll('.gallery-item img').forEach(img => {
            const option = document.createElement('div');
            option.className = 'custom-select-option';
            option.textContent = img.alt;
            option.dataset.path = img.src;

            option.addEventListener('click', function() {
                sourceImageInput.value = img.alt;
                sourceImageSelect.classList.remove('active');
            });

            sourceImageOptions.appendChild(option);
        });
    }

    populateSourceImages();

    // 源图片输入框事件
    sourceImageInput.addEventListener('focus', () => sourceImageSelect.classList.add('active'));
    sourceImageInput.addEventListener('input', filterSourceImageOptions);
    document.addEventListener('click', function(e) {
        if (!sourceImageSelect.contains(e.target)) {
            sourceImageSelect.classList.remove('active');
        }
    });

    function filterSourceImageOptions() {
        const searchTerm = sourceImageInput.value.toLowerCase();
        sourceImageOptions.querySelectorAll('.custom-select-option').forEach(option => {
            option.style.display = option.textContent.toLowerCase().includes(searchTerm) ? 'block' : 'none';
        });
    }

    // 生成图片
    generateBtn.addEventListener('click', async function() {
        const selectedImageName = sourceImageInput.value;
        const selectedImage = [...document.querySelectorAll('.gallery-item img')]
            .find(img => img.alt === selectedImageName);
        const style = styleInput.value;
        const deviation = document.getElementById('deviation').value;
        const customPrompt = document.getElementById('custom-prompt').value;

        if (!selectedImageName) return alert('请选择或输入源图片名称');
        if (!selectedImage && !confirm('未找到匹配的图片，是否继续？')) return;
        if (!style) return alert('请选择或输入图片风格');

        loadingSpinner.style.display = 'block';
        placeholderText.style.display = 'none';
        generatedImage.style.display = 'none';

        try {
            const account = getAccountInfo();
            const clientIP = await getClientIP();
            const Domain = await getBothDomains();
            const response = await fetch(`${Domain.proxyDomain}${Domain.localhostDomain}/picture-diffusion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Client-IP': clientIP,
                    'X-User-Agent': navigator.userAgent
                },
                body: JSON.stringify({
                    imgUrl: selectedImage?.src || '',
                    'account': sha256Hash(account),
                    style,
                    deviation,
                    customPrompt
                })
            });

            if (!response.ok) throw new Error('网络响应不正常');

            const data = await response.json();
            if (!data.success) {
                console.error('生成图片失败:', data.message);
                placeholderText.textContent = `图片生成失败: ${data.message}`;
                placeholderText.style.display = 'block';
            }else if (!data.outUrl) {
                throw new Error('API返回数据格式不正确')
            };

            generatedImage.src = data.outUrl;
            generatedImage.style.display = 'block';
            initGeneratedImageLightbox();
        } catch (error) {
            console.error('生成图片失败:', error);
            placeholderText.textContent = `图片生成失败: ${error.message}`;
            placeholderText.style.display = 'block';
        } finally {
            loadingSpinner.style.display = 'none';
        }
    });

    // 生成的图片lightbox
    function initGeneratedImageLightbox() {
        const generatedLightbox = document.getElementById('generated-lightbox');
        const generatedLightboxContent = document.getElementById('generated-lightbox-content');
        const generatedLightboxClose = document.getElementById('generated-lightbox-close');

        generatedImage.addEventListener('click', function() {
            if (generatedImage.style.display === 'block' && generatedImage.src) {
                generatedLightboxContent.innerHTML = `<img src="${generatedImage.src}" alt="生成的图片">`;
                generatedLightbox.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        });

        generatedLightboxClose.addEventListener('click', () => {
            generatedLightbox.style.display = 'none';
            document.body.style.overflow = 'auto';
        });

        generatedLightbox.addEventListener('click', function(e) {
            if (e.target === generatedLightbox) {
                generatedLightbox.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && generatedLightbox.style.display === 'flex') {
                generatedLightbox.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
}

// 股票策略表现
async function loadStrategyPerformance() {
    try {
        const container = document.getElementById('stock-chart-container');
        const account = getAccountInfo();
        const clientIP = await getClientIP();
        const Domain = await getBothDomains();

        // 显示加载状态
        container.innerHTML = '<div class="loading-spinner"></div>';

        const response = await fetch(`${Domain.proxyDomain}${Domain.localhostDomain}/quant`, {
            headers: {
                'X-Client-IP': clientIP,
                'X-User-Agent': navigator.userAgent,
                'X-Account': sha256Hash(account) // GET方法不能有body，说以放headers里
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            showChartError(`加载失败: ${data.message}` || 'Unknown server error.');
            return;
        }

        // 更新基本指标
        updateBasicMetrics(data.output.data.basic_metrics);

        // 动态加载Chart.js
        if (typeof Chart === 'undefined') {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }

        // 绘制图表
        renderReturnsChart(data.output.data.cumulative_returns);

    } catch (error) {
        console.error('加载策略表现失败:', error);
        showChartError(`加载失败: ${error.message}`);
    }
}


// 显示图表错误
function showChartError(message) {
    const container = document.getElementById('stock-chart-container');
    container.innerHTML = `
        <div class="chart-error">
            <p>${message}</p>
            <button onclick="loadStrategyPerformance()" class="retry-btn">
                重新加载
            </button>
        </div>
    `;
}


// 更新基本指标
function updateBasicMetrics(metrics) {
    // HS300累计收益
    updateMetricCard(1,
        metrics.hs300_cumulative_return,
        `${metrics.hs300_cumulative_return > 0 ? '+' : ''}${metrics.hs300_cumulative_return.toFixed(4)}%`,
        '今年'
    );

    // 策略累计收益
    updateMetricCard(2,
        metrics.strategy_cumulative_return,
        `${metrics.strategy_cumulative_return > 0 ? '+' : ''}${metrics.strategy_cumulative_return.toFixed(4)}%`,
        '今年'
    );

    // HS300今天收益
    updateMetricCard(3,
        metrics.hs300_today_return,
        `${metrics.hs300_today_return > 0 ? '+' : ''}${metrics.hs300_today_return.toFixed(4)}%`,
        `${metrics.timestamp}`
    );

    // 策略今天收益
    updateMetricCard(4,
        metrics.strategy_today_return,
        `${metrics.strategy_today_return > 0 ? '+' : ''}${metrics.strategy_today_return.toFixed(4)}%`,
        `${metrics.timestamp}`
    );

    // 明天信号
    const signalElement = document.querySelector('.metric-card:nth-child(5) .signal-indicator');
    if (metrics.tomorrow_signal === 'buy') {
        signalElement.textContent = '买入';
        signalElement.className = 'signal-indicator signal-buy';
    } else if (metrics.tomorrow_signal === 'sell') {
        signalElement.textContent = '卖出';
        signalElement.className = 'signal-indicator signal-sell';
    } else {
        signalElement.textContent = '持有';
        signalElement.className = 'signal-indicator signal-hold';
    }
    document.querySelector('.metric-card:nth-child(5) .signal-confidence').textContent =
        `置信度: ${metrics.tomorrow_signal_confidence}%`;

    // 明天最优ETF
    const etfElement = document.querySelector('.metric-card:nth-child(6) .etf-info');
    etfElement.innerHTML = `
        <div class="etf-name">${metrics.tomorrow_best_etf.name}</div>
        <div class="etf-code">${metrics.tomorrow_best_etf.code}</div>
    `;

    // 更新最大回撤指标 (第8个卡片)
    updateMetricCard(8,
        -Math.abs(metrics.max_back_step), // 确保为负值
        `${metrics.max_back_step.value.toFixed(4)}%`,
        `${metrics.max_back_step.date_range.max_back_step_begin} To ${metrics.max_back_step.date_range.max_back_step_end}`
    );

    // 更新胜率指标 (第7个卡片)
    updateMetricCard(7,
        metrics.winning_rate,
        `${(metrics.winning_rate * 100).toFixed(4)}%`,
        '今年'
    );
}

// 更新指标卡片通用函数（支持百分比和非百分比值的显示）
function updateMetricCard(index, value, displayValue, period) {
    const card = document.querySelector(`.metric-card:nth-child(${index})`);
    if (!card) return;

    const valueElement = card.querySelector('.metric-value');
    const periodElement = card.querySelector('.metric-period, .metric-date');

    valueElement.textContent = displayValue;

    // 特殊处理胜率（不需要正负号）
    if (index === 7) {
        valueElement.className = 'metric-value positive';
    }
    // 特殊处理最大回撤（总是显示为负值）
    else if (index === 8) {
        valueElement.className = 'metric-value negative';
    }
    // 其他指标保持原有逻辑
    else {
        valueElement.className = `metric-value ${value >= 0 ? 'positive' : 'negative'}`;
    }

    if (periodElement) {
        periodElement.textContent = `(${period})`;
    }
}

// 绘制收益走势图
function renderReturnsChart(returnsData) {
    const container = document.getElementById('stock-chart-container');

    // 清空容器并创建新的canvas
    container.innerHTML = '';
    const canvas = document.createElement('canvas');
    canvas.id = 'stock-chart';
    container.appendChild(canvas);

    // 确保容器有正确的高度
    container.style.height = '400px';
    container.style.position = 'relative';

    // 获取绘图上下文
    const ctx = canvas.getContext('2d');

    // 确保有有效数据
    if (!returnsData || !returnsData.date || returnsData.date.length === 0) {
        showChartError('无有效数据可显示');
        return;
    }

    // 销毁旧图表实例
    if (window.returnsChart) {
        window.returnsChart.destroy();
    }

    // 创建新图表
    window.returnsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: returnsData.date.map(date => formatDate(date)),
            datasets: [
                {
                    label: '策略累计收益',
                    data: returnsData.strategy_returns,
                    borderColor: '#4a89dc',
                    backgroundColor: 'rgba(74, 137, 220, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'HS300累计收益',
                    data: returnsData.hs300_returns,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '策略与HS300累计收益对比',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(4)}%`;
                        }
                    }
                },
                legend: {
                    position: 'top',
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    grid: {
                        color: '#eaeaea'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(0) + '%';
                        }
                    }
                }
            }
        }
    });
}


// 格式化日期
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? dateStr :
        `${date.getMonth() + 1}月${date.getDate()}日`;
}


// 抢票功能初始化
function initTicketGrab() {
    const grabBtn = document.getElementById('grab-btn');
    const timeSlotCheckboxes = document.querySelectorAll('input[name="time-slot"]');
    const ticketSpinner = document.getElementById('ticket-spinner');
    const ticketModal = document.getElementById('ticket-modal');
    const modalClose = document.getElementById('modal-close');
    const resultTitle = document.getElementById('result-title');
    const resultMessage = document.getElementById('result-message');
    const resultDetails = document.getElementById('result-details');

    // 抢票按钮点击事件
    grabBtn.addEventListener('click', async function() {
        // 获取所有选中的时间段（数组形式）
        const selectedSlots = Array.from(timeSlotCheckboxes)
            .filter(checkbox => checkbox.checked)
            .map(checkbox => checkbox.value);

        if (selectedSlots.length === 0) {
            alert('请至少选择一个场次');
            return;
        }

        grabBtn.disabled = true;
        ticketSpinner.style.display = 'block';

        try {
            // 改为一次性发送所有时间段到后端
            const result = await grabTickets(selectedSlots); // 批量发要抢的时间段
            if (!result.success) {
                showResult(result.success, result.message, result.message);
            } else {
                showResult(result.output.success, result.output.message, result.output.details);
            }
        } catch (error) {
            showResult(false, '抢票失败', error.message);
        } finally {
            grabBtn.disabled = false;
            ticketSpinner.style.display = 'none';
        }
    });

    // 关闭弹窗事件
    modalClose.addEventListener('click', function() {
        ticketModal.style.display = 'none';
    });

    // 点击弹窗外部关闭
    ticketModal.addEventListener('click', function(e) {
        if (e.target === ticketModal) {
            ticketModal.style.display = 'none';
        }
    });

    // 抢票函数
    async function grabTickets(timeSlots) {
        try {
            const account = getAccountInfo();
            const clientIP = await getClientIP();
            const Domain = await getBothDomains();
            const response = await fetch(`${Domain.proxyDomain}${Domain.localhostDomain}/grab-tickets`, { // 注意接口URL改为复数形式
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Client-IP': clientIP,
                    'X-User-Agent': navigator.userAgent
                },
                body: JSON.stringify({
                    timeSlots, // 数组格式：["09:30-10:30", "10:30-11:30"]
                    date: getTomorrowDate(),
                    'account': sha256Hash(account)
                })
            });

            if (!response.ok) {
                throw new Error('Internet error')
            }
            return await response.json();
        } catch (error) {
            console.error('批量抢票失败:', error);
            throw error;
        }
    }

    // 显示多个结果
    function showResult(success, message, details) {
        resultTitle.textContent = success ? '抢票结果' : '抢票失败';
        resultTitle.style.color = success ? '#27ae60' : '#e74c3c';

        // 如果details是数组，展示每个时间段的结果
        if (Array.isArray(details)) {
            resultMessage.innerHTML = details.map(d => `
                <div class="result-item ${d.success ? 'success' : 'fail'}">
                    ${d.timeSlot}: ${d.success ? '✅' : '❌'} ${d.court || d.reason ||  ''}
                </div>
            `).join('');
        } else {
            resultMessage.textContent = message;
        }

        ticketModal.style.display = 'flex';
    }

    // 获取明天日期的辅助函数
    function getTomorrowDate() {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);

        return `${tomorrow.getFullYear()}年${tomorrow.getMonth() + 1}月${tomorrow.getDate()}日`;
    }
}

// AI对话功能初始化
function initAIChat() {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const clearChatBtn = document.getElementById('clear-chat');
    const copyChatBtn = document.getElementById('copy-chat');
    const chatSpinner = document.getElementById('chat-spinner');

    // 加载历史记录，兼容新数据结构
    let chatHistory = [];
    try {
        const saved = localStorage.getItem('aiChatHistory');
        if (saved) {
            chatHistory = JSON.parse(saved);
            // 验证数据格式，确保包含必要的字段
            chatHistory = chatHistory.filter(msg =>
                msg && typeof msg === 'object' &&
                msg.usr_content && msg.ass_content
            );
        }
    } catch (error) {
        console.error('加载聊天历史失败:', error);
        chatHistory = [];
    }

    // 初始化界面
    initializeChatInterface();

    // 发送消息
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 清空对话
    clearChatBtn.addEventListener('click', function() {
        if (confirm('确定要清空对话记录吗？')) {
            chatHistory = [];
            saveChatHistory();
            initializeChatInterface();
        }
    });

    // 复制对话
    copyChatBtn.addEventListener('click', copyChatHistory);

    function initializeChatInterface() {
        chatMessages.innerHTML = '';

        if (chatHistory.length === 0) {
            // 显示欢迎消息
            addMessageToChat('bot', '您好！我是您的AI助手，收录了150万张食谱，有什么可以帮您的吗？');
        } else {
            // 加载历史消息 - 使用新的数据结构
            chatHistory.forEach(msg => {
                // 先显示用户消息
                addMessageToChat('user', msg.usr_content);
                // 再显示AI回复
                addMessageToChat('bot', msg.ass_content);
            });
        }
        scrollToBottom();
    }

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // 禁用输入和按钮
        chatInput.disabled = true;
        sendButton.disabled = true;

        // 添加用户消息到界面
        addMessageToChat('user', message);
        chatInput.value = '';

        // 显示加载状态
        chatSpinner.style.display = 'block';
        scrollToBottom();

        try {
            // 调用AI对话API
            const response = await callAIChatAPI(message);

            // 添加AI回复到界面
            addMessageToChat('bot', response);

            // 保存到历史记录 - 使用新的数据结构
            chatHistory.push({
                usr_content: message,      // 用户发送的内容
                ass_content: response,     // AI回复的内容
                timestamp: new Date().toISOString()
            });

            // 限制历史记录长度（最近30轮对话）
            if (chatHistory.length > 30) {
                chatHistory = chatHistory.slice(-30);
            }

            saveChatHistory();

        } catch (error) {
            console.error('AI对话失败:', error);
            addMessageToChat('bot', `抱歉，我暂时无法响应。${error.message}`);
        } finally {
            // 恢复输入和按钮
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatSpinner.style.display = 'none';
            chatInput.focus();
        }
    }

    async function callAIChatAPI(message) {
        const account = getAccountInfo();
        const clientIP = await getClientIP();
        const Domain = await getBothDomains();

        // 构建发送给后端的history格式

        const response = await fetch(`${Domain.proxyDomain}${Domain.localhostDomain}/ai-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Client-IP': clientIP,
                'X-User-Agent': navigator.userAgent
            },
            body: JSON.stringify({
                message: message,
                'account': sha256Hash(account),
                history: chatHistory.slice(-5) // 发送最近5轮用户消息作为上下文
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || 'AI服务返回错误');
        }

        return data.output || '抱歉，我没有理解您的问题。';
    }

    function addMessageToChat(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;

        const timestamp = new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });

        messageDiv.innerHTML = `
            <div class="message-avatar">${role === 'user' ? 'M' : 'AI'}</div>
            <div class="message-content">
                <p>${content.replace(/\n/g, '<br>')}</p>
                <div class="message-time">${timestamp}</div>
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function saveChatHistory() {
        try {
            localStorage.setItem('aiChatHistory', JSON.stringify(chatHistory));
        } catch (error) {
            console.error('保存聊天历史失败:', error);
        }
    }

    function copyChatHistory() {
        const chatText = Array.from(chatMessages.querySelectorAll('.message'))
            .map(msg => {
                const role = msg.classList.contains('user-message') ? 'M' : 'AI';
                const content = msg.querySelector('.message-content p').textContent;
                return `${role}: ${content}`;
            })
            .join('\n\n');

        navigator.clipboard.writeText(chatText).then(() => {
            alert('对话已复制到剪贴板！');
        }).catch(() => {
            alert('复制失败，请手动选择文本复制。');
        });
    }

    // 自动聚焦到输入框
    chatInput.focus();
}