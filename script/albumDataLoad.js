
function sha256Hash(message, salt = '') {
  const saltedMessage = message + salt;
  return CryptoJS.SHA256(saltedMessage).toString(CryptoJS.enc.Hex);
}

const localhostDomain = fetch('customize.json')
    .then(response => response.json())
    .then(data => data.localhostDomain)

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
    initAccountInput()
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
            const src = `album/${gallery.prefix}/${i}.jpg`;

            appState.allImages.push({ src, alt });

            container.innerHTML += `
                <div class="gallery-item" data-index="${itemIndex}">
                    <img src="${src}" alt="${alt}" loading="lazy">
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

// 获取客户端IP地址（异步）
async function getClientIP() {
    try {
        // 使用第三方API获取IP（注意：生产环境建议通过后端获取）
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        return data.ip || 'unknown';
    } catch (error) {
        console.error('获取IP地址失败:', error);
        return 'unknown';
    }
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
            const Domain = await localhostDomain;
            const account = getAccountInfo();
            const clientIP = await getClientIP();
            const response = await fetch(`${Domain}/picture-diffusion`, {
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
        const Domain = await localhostDomain;
        const account = getAccountInfo();
        const clientIP = await getClientIP();

        // 显示加载状态
        container.innerHTML = '<div class="loading-spinner"></div>';

        const response = await fetch(`${Domain}/quant`, {
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
            const Domain = await localhostDomain;
            const account = getAccountInfo();
            const clientIP = await getClientIP();
            const response = await fetch(`${Domain}/grab-tickets`, { // 注意接口URL改为复数形式
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