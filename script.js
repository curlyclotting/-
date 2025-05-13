document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const inputField = document.getElementById('question');
    const sendButton = document.getElementById('submit');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const themeToggle = document.getElementById('themeToggle');
    const rightSidebar = document.querySelector('.right-sidebar');
    const scrollToBottomBtn = document.getElementById('scrollToBottom');


    const toggleTheme = () => {
        const isDark = document.body.getAttribute('data-theme') === 'dark';
        document.body.setAttribute('data-theme', isDark ? 'light' : 'dark');
        themeToggle.innerHTML = `<i class="fas fa-${isDark ? 'moon' : 'sun'}"></i>`;
        localStorage.setItem('theme', isDark ? 'light' : 'dark');
    };


    const initTheme = () => {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);
        themeToggle.innerHTML = `<i class="fas fa-${savedTheme === 'dark' ? 'sun' : 'moon'}"></i>`;
    };

 
    function showReferences(references) {
        const content = document.querySelector('.reference-content');
        content.innerHTML = '';
        
        references.forEach((ref, index) => {
            const item = document.createElement('div');
            item.className = 'reference-item';
            item.innerHTML = `
                <div class="reference-text">${ref.text}</div>
                <div class="score">相关度：${(ref.score * 100).toFixed(1)}%</div>
            `;
            content.appendChild(item);
        });
        
        if (window.innerWidth <= 1024) {
            rightSidebar.classList.add('active');
        }
    }


    document.querySelector('.main-content').addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && rightSidebar.classList.contains('active')) {
            rightSidebar.classList.remove('active');
        }
    });


    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }


    function updateScrollButton() {
        const scrollPosition = chatContainer.scrollTop;
        const scrollHeight = chatContainer.scrollHeight;
        const clientHeight = chatContainer.clientHeight;
        const threshold = 100;
        
        if (scrollHeight - scrollPosition - clientHeight > threshold) {
            scrollToBottomBtn.classList.add('visible');
        } else {
            scrollToBottomBtn.classList.remove('visible');
        }
    }

    function formatTime(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }


    const MAX_HISTORY = 50;
    let messageHistory = [];
    let currentHistoryIndex = -1;


    function updateSuggestions(input) {
        const suggestions = document.querySelector('.input-suggestions');
        if (!input.trim()) {
            suggestions.style.display = 'flex';
            return;
        }
        suggestions.style.display = 'none';
    }


    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'system'}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const icon = document.createElement('i');
        icon.className = isUser ? 'fas fa-user' : 'fas fa-robot';
        avatar.appendChild(icon);
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (content.includes('\n')) {

            content.split('\n').forEach((line, index) => {
                if (line.trim()) {
                    const p = document.createElement('p');
                    p.textContent = line;
                    p.style.animation = `fadeIn 0.3s ${index * 0.1}s forwards`;
                    messageContent.appendChild(p);
                }
            });
        } else {
            const p = document.createElement('p');
            p.textContent = content;
            messageContent.appendChild(p);
        }
        

        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = formatTime(new Date());
        messageContent.appendChild(timestamp);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        chatContainer.appendChild(messageDiv);
        

        updateScrollButton();
        

        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message system typing-message';
        indicator.innerHTML = `
            <div class="avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        `;
        chatContainer.appendChild(indicator);
        scrollToBottom();
        return indicator;
    }

    mapboxgl.accessToken = 'pk.eyJ1IjoiZm9lZ2Nvc3YiLCJhIjoiY205dzFta2ZqMDhuYTJzcTBpbTAyM3phaCJ9.08d_VBSI8P28MZ8_cZc3pg';
    

    function debug(message, data = null) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] ${message}`, data || '');
    }


    let currentMarker = null;

    let map;
    function initMap() {
        debug('开始初始化地图');
        try {
            map = new mapboxgl.Map({
                container: 'map',
                style: 'mapbox://styles/mapbox/streets-v11',
                center: [119.42, 31.96],
                zoom: 10
            });

            map.on('load', () => {
                debug('地图加载完成');
            });


            map.on('click', (e) => {
                const coordinates = [e.lngLat.lng, e.lngLat.lat];
                debug('地图被点击，坐标：', coordinates);
                

                const existingPopups = document.querySelectorAll('.mapboxgl-popup');
                existingPopups.forEach(popup => popup.remove());


                const popup = new mapboxgl.Popup({
                    closeButton: true,
                    closeOnClick: false,
                    anchor: 'top-left'
                })
                .setLngLat(coordinates)
                .setHTML(`
                    <div class="popup-content">
                        <h4>标记点</h4>
                    </div>
                `)
                .addTo(map);
            });

            map.on('error', (e) => {
                debug('地图加载错误', e);
            });


            const mapContainer = document.getElementById('map');
            if (mapContainer) {
                mapContainer.style.display = 'block';
                debug('地图容器已设置为可见');
            }
        } catch (error) {
            debug('地图初始化失败', error);
        }
    }

    function parseCoordinates(text) {
        const regex = /北纬([\d.]+)°.*东经([\d.]+)°/;
        const match = text.match(regex);
        if (match) {
            const lat = parseFloat(match[1]);
            const lng = parseFloat(match[2]);
            console.log('解析到坐标:', [lng, lat]);
            return [lng, lat];
        }
        console.log('未找到坐标信息');
        return null;
    }

    function addMarkerToMap(coordinates, info = null) {
        if (!coordinates || coordinates.length !== 2) {
            console.error('无效的坐标:', coordinates);
            return;
        }

        console.log('正在添加标记到坐标:', coordinates);

        if (!map) {
            console.error('地图未初始化');
            return;
        }


        const existingPopups = document.querySelectorAll('.mapboxgl-popup');
        existingPopups.forEach(popup => popup.remove());


        const popup = new mapboxgl.Popup({
            closeButton: true,
            closeOnClick: false,
            anchor: 'top-left',
            maxWidth: '300px'
        })
        .setLngLat(coordinates)
        .setHTML(`
            <div class="popup-content">
                <h4>应急地点</h4>
                ${info ? `<p>${info}</p>` : ''}
            </div>
        `)
        .addTo(map);

        map.flyTo({
            center: coordinates,
            zoom: 13,
            essential: true,
            duration: 2000
        });

        console.log('标记添加完成');
    }


    async function submitQuestion(question) {
        if (!question.trim()) return;
        
        document.body.classList.add('loading');
        debug('提交问题:', question);
        
        addMessage(question, true);
        inputField.value = '';
        updateSuggestions('');
        
        const loadingIndicator = showTypingIndicator();
        
        try {
            const response = await fetch('http://127.0.0.1:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: question })
            });
            
            debug('服务器响应状态:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }
            
            const data = await response.json();
            debug('收到服务器响应:', data);
            
            loadingIndicator.remove();
            
            if (data.status === 'error') {
                throw new Error(data.answer || '服务器处理失败');
            }
            
            addMessage(data.answer);
            
            if (data.contexts && data.contexts.length > 0) {
                showReferences(data.contexts);
                debug('显示参考资料');
            }
            
        } catch (error) {
            debug('请求处理错误:', error);
            loadingIndicator.remove();
            addMessage(`错误: ${error.message}\n请检查服务器连接或稍后重试。`);
        } finally {
            document.body.classList.remove('loading');
        }
    }


    const originalAddMessage = addMessage;
    window.addMessage = function(message, isUser = false) {
        originalAddMessage(message, isUser);
        
        if (!isUser) {
            const coordinates = parseCoordinates(message);
            if (coordinates) {
                console.log('检测到坐标信息，更新地图'); // 添加调试日志
                addMarkerToMap(coordinates);
            }
        }
    };


    inputField.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowUp' && e.altKey) {
            e.preventDefault();
            if (currentHistoryIndex < messageHistory.length - 1) {
                currentHistoryIndex++;
                inputField.value = messageHistory[currentHistoryIndex];
            }
        } else if (e.key === 'ArrowDown' && e.altKey) {
            e.preventDefault();
            if (currentHistoryIndex > 0) {
                currentHistoryIndex--;
                inputField.value = messageHistory[currentHistoryIndex];
            } else if (currentHistoryIndex === 0) {
                currentHistoryIndex = -1;
                inputField.value = '';
            }
        }
    });

    inputField.addEventListener('focus', () => {
        document.querySelector('.input-wrapper').classList.add('focused');
    });

    inputField.addEventListener('blur', () => {
        document.querySelector('.input-wrapper').classList.remove('focused');
    });


    inputField.addEventListener('input', (e) => {
        updateSuggestions(e.target.value);
    });


    themeToggle.addEventListener('click', toggleTheme);


    sendButton.addEventListener('click', () => {
        const question = inputField.value;
        if (question.trim()) {
            submitQuestion(question);
            inputField.value = '';
        }
    });


    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendButton.click();
        }
    });


    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.textContent;
            inputField.value = question;
            submitQuestion(question);
        });
    });


    chatContainer.addEventListener('scroll', updateScrollButton);
    

    scrollToBottomBtn.addEventListener('click', () => {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    });


    function init() {
        debug('开始系统初始化');
        initTheme();
        initMap();
        inputField.focus();
        updateScrollButton();
        debug('系统初始化完成');
    }

    init();
});
