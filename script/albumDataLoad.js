// 音乐播放器功能
        const musicPlayer = document.getElementById('music-player');
        const bgMusic = document.getElementById('bg-music');

        // 初始化音乐播放状态
        let isMusicPlaying = false;

        // 点击音乐播放按钮
        musicPlayer.addEventListener('click', function() {
            if (isMusicPlaying) {
                bgMusic.pause();
                musicPlayer.classList.remove('playing');
            } else {
                bgMusic.play()
                    .then(() => {
                        musicPlayer.classList.add('playing');
                    })
                    .catch(error => {
                        console.error('自动播放被阻止:', error);
                        // 用户可能需要先交互才能播放
                        musicPlayer.textContent = '点击播放音乐';
                    });
            }
            isMusicPlaying = !isMusicPlaying;
        });

        // 用户第一次交互后尝试自动播放
        document.body.addEventListener('click', function initMusic() {
            if (!isMusicPlaying) {
                bgMusic.play()
                    .then(() => {
                        musicPlayer.classList.add('playing');
                        isMusicPlaying = true;
                    })
                    .catch(error => {
                        console.log('需要用户明确点击播放按钮');
                    });
            }
            document.body.removeEventListener('click', initMusic);
        }, { once: true });

        // 存储所有图片元素以便导航
        let allImages = [];
        let currentImageIndex = 0;

        // 添加武功山图片 (1-27.jpg)
        const kongfuGallery = document.getElementById('kongfu-gallery');
        for (let i = 1; i <= 27; i++) {
            // 记录图片信息
            const itemIndex = allImages.length;
            let alt = "kongfu"+i;
            allImages.push({
                src: "album/kongfu/"+i+".jpg",
                alt: alt
            });

            kongfuGallery.innerHTML += `
                <div class="gallery-item" data-index="${itemIndex}">
                    <img src="album/kongfu/${i}.jpg" alt=${alt} loading="lazy">
                    <div class="image-caption">${alt}</div>
                </div>
            `;
        }

        // 添加济州岛图片 (1-52.jpg)
        const jejuGallery = document.getElementById('jeju-gallery');
        for (let i = 1; i <= 51; i++) {
            // 记录图片信息
            const itemIndex = allImages.length;
            let alt = "jeju"+i;
            allImages.push({
                src: "album/jeju/"+i+".jpg",
                alt: alt
            });

            jejuGallery.innerHTML += `
                <div class="gallery-item" data-index="${itemIndex}">
                    <img src="album/jeju/${i}.jpg" alt=${alt} loading="lazy">
                    <div class="image-caption">${alt}</div>
                </div>
            `;
        }

        // 添加其他图片 (1-5.jpg)
        const elseGallery = document.getElementById('else-gallery');
        for (let i = 1; i <= 5; i++) {
            // 记录图片信息
            const itemIndex = allImages.length;
            let alt = "else"+i;
            allImages.push({
                src: "album/else/"+i+".jpg",
                alt: alt
            });

            elseGallery.innerHTML += `
                <div class="gallery-item" data-index="${itemIndex}">
                    <img src="album/else/${i}.jpg" alt=${alt} loading="lazy">
                    <div class="image-caption">${alt}</div>
                </div>
            `;
        }

        // 移动端长按显示图片名称
        let touchTimer = null;
        document.addEventListener('touchstart', function(e) {
            const galleryItem = e.target.closest('.gallery-item');
            if (galleryItem) {
                touchTimer = setTimeout(() => {
                    galleryItem.classList.add('show-caption');
                    touchTimer = null;
                }, 500); // 长按500毫秒后显示
            }
        }, { passive: true });

        document.addEventListener('touchend', function(e) {
            if (touchTimer) {
                clearTimeout(touchTimer);
                touchTimer = null;
            }
            const galleryItem = e.target.closest('.gallery-item');
            if (galleryItem) {
                galleryItem.classList.remove('show-caption');
            }
        }, { passive: true });

        // 获取lightbox元素
        const lightbox = document.getElementById('lightbox');
        const lightboxContent = document.getElementById('lightbox-content');
        const lightboxClose = document.getElementById('lightbox-close');
        const lightboxPrev = document.getElementById('lightbox-prev');
        const lightboxNext = document.getElementById('lightbox-next');

        // 点击图片打开lightbox
        document.addEventListener('click', function(e) {
            // 修改这里：先检查是否点击了图片，然后找到最近的gallery-item
            const imgElement = e.target.closest('.gallery-item img');
            if (imgElement) {
                const galleryItem = imgElement.closest('.gallery-item');
                if (galleryItem) {
                    const index = parseInt(galleryItem.getAttribute('data-index'));
                    if (!isNaN(index)) {
                        currentImageIndex = index;
                        openLightbox();
                    }
                }
            }
        });

        // 打开lightbox
        function openLightbox() {
            const image = allImages[currentImageIndex];
            lightboxContent.innerHTML = `<img src="${image.src}" alt="${image.alt}">`;
            lightbox.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // 防止背景滚动
        }

        // 关闭lightbox
        function closeLightbox() {
            lightbox.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        // 导航到上一张图片
        function prevImage() {
            currentImageIndex = (currentImageIndex - 1 + allImages.length) % allImages.length;
            openLightbox();
        }

        // 导航到下一张图片
        function nextImage() {
            currentImageIndex = (currentImageIndex + 1) % allImages.length;
            openLightbox();
        }

        // 绑定事件
        lightboxClose.addEventListener('click', closeLightbox);
        lightboxPrev.addEventListener('click', prevImage);
        lightboxNext.addEventListener('click', nextImage);

        // 按ESC键关闭lightbox
        document.addEventListener('keydown', function(e) {
            if (lightbox.style.display === 'flex') {
                if (e.key === 'Escape') {
                    closeLightbox();
                } else if (e.key === 'ArrowLeft') {
                    prevImage();
                } else if (e.key === 'ArrowRight') {
                    nextImage();
                }
            }
        });

        // 点击lightbox背景关闭
        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox) {
                closeLightbox();
            }
        });

        // 新增的Diffusion功能代码
        document.addEventListener('DOMContentLoaded', function() {
            // 获取DOM元素
            const sourceImageInput = document.getElementById('source-image-input');
            const sourceImageOptions = document.getElementById('source-image-options');
            const styleInput = document.getElementById('style-input');
            const generateBtn = document.getElementById('generate-btn');
            const generatedImage = document.getElementById('generated-image');
            const placeholderText = document.getElementById('placeholder-text');
            const loadingSpinner = document.getElementById('loading-spinner');
            const sourceImageSelect = document.getElementById('source-image-select');

            // 存储所有图片信息
            const allImages = [];

            // 动态填充源图片选择框
            function populateSourceImages() {
                // 清空现有选项
                sourceImageOptions.innerHTML = '';

                // 获取所有图片的alt和src
                const images = document.querySelectorAll('.gallery-item img');

                images.forEach(img => {
                    allImages.push({
                        name: img.alt,
                        path: img.src
                    });

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

            // 调用函数填充图片选择框
            populateSourceImages();

            // 源图片输入框事件处理
            sourceImageInput.addEventListener('focus', function() {
                sourceImageSelect.classList.add('active');
                filterSourceImageOptions();
            });

            sourceImageInput.addEventListener('input', function() {
                filterSourceImageOptions();
            });

            document.addEventListener('click', function(e) {
                if (!sourceImageSelect.contains(e.target)) {
                    sourceImageSelect.classList.remove('active');
                }
            });

            // 过滤源图片选项
            function filterSourceImageOptions() {
                const searchTerm = sourceImageInput.value.toLowerCase();
                const options = sourceImageOptions.querySelectorAll('.custom-select-option');

                options.forEach(option => {
                    const text = option.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        option.style.display = 'block';
                    } else {
                        option.style.display = 'none';
                    }
                });
            }

            // 生成图片按钮点击事件
            generateBtn.addEventListener('click', async function() {
                const selectedImageName = sourceImageInput.value;
                const selectedImage = allImages.find(img => img.name === selectedImageName);
                const style = styleInput.value;
                const deviation = document.getElementById('deviation').value;
                const customPrompt = document.getElementById('custom-prompt').value; // 获取自定义描述

                if (!selectedImageName) {
                    alert('请选择或输入源图片名称');
                    return;
                }

                if (!selectedImage && !confirm('未找到匹配的图片，是否使用自定义图片名称继续？')) {
                    return;
                }

                if (!style) {
                    alert('请选择或输入图片风格');
                    return;
                }

                // 显示加载中
                loadingSpinner.style.display = 'block';
                placeholderText.style.display = 'none';
                generatedImage.style.display = 'none';

                try {
                    // 调用大模型API (这里需要替换为实际的API调用)
                    const imagePath = selectedImage ? selectedImage.path : '';
                    await callDiffusionAPI(imagePath, style, deviation, customPrompt);

                } catch (error) {
                    // 错误已在callDiffusionAPI中处理
                } finally {
                    loadingSpinner.style.display = 'none';
                }
            });

            const localhostDomain = fetch('customize.json')
                .then(response => response.json())
                .then(data => data.localhostDomain) // 获取localhost的穿透域名

            // 模拟调用大模型API的函数
            async function callDiffusionAPI(imageUrl, style, deviation, customPrompt) {
                try {
                    const Domain = await localhostDomain;
                    const response = await fetch(`${Domain}/picture-diffusion`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            imgUrl: imageUrl,
                            style: style,
                            deviation: deviation,
                            customPrompt: customPrompt
                        })
                    });

                    if (!response.ok) {
                        throw new Error('网络响应不正常');
                    }

                    const data = await response.json();

                    if (!data.outUrl) {
                        throw new Error('API返回数据格式不正确');
                    }

                    // 直接在这里更新图片显示
                    generatedImage.src = data.outUrl;
                    generatedImage.style.display = 'block';
                    placeholderText.style.display = 'none';

                    return data.outUrl;
                } catch (error) {
                    console.error('生成图片失败:', error);
                    placeholderText.textContent = '图片生成失败: ' + error.message;
                    placeholderText.style.display = 'block';
                    throw error; // 重新抛出错误以便外部捕获
                }
            }
        });

        // 获取生成的图片lightbox元素
        const generatedLightbox = document.getElementById('generated-lightbox');
        const generatedLightboxContent = document.getElementById('generated-lightbox-content');
        const generatedLightboxClose = document.getElementById('generated-lightbox-close');
        const generatedImage = document.getElementById('generated-image');

        // 点击生成的图片打开lightbox
        generatedImage.addEventListener('click', function() {
            if (generatedImage.style.display === 'block' && generatedImage.src) {
                generatedLightboxContent.innerHTML = `<img src="${generatedImage.src}" alt="生成的图片">`;
                generatedLightbox.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        });

        // 关闭生成的图片lightbox
        generatedLightboxClose.addEventListener('click', function() {
            generatedLightbox.style.display = 'none';
            document.body.style.overflow = 'auto';
        });

        // 点击背景关闭
        generatedLightbox.addEventListener('click', function(e) {
            if (e.target === generatedLightbox) {
                generatedLightbox.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });

        // 按ESC键关闭
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && generatedLightbox.style.display === 'flex') {
                generatedLightbox.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });