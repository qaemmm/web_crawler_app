/**
 * Cookie管理模块
 */

class CookieManager {
    constructor() {
        this.currentCookie = '';
        this.cookieList = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCookieList();
    }

    bindEvents() {
        // Cookie输入框事件
        const cookieInput = document.getElementById('cookieInput');
        const validateBtn = document.getElementById('validateCookieBtn');
        const saveCookieBtn = document.getElementById('saveCookieBtn');
        const loadCookieBtn = document.getElementById('loadCookieBtn');

        if (cookieInput) {
            // 实时验证Cookie格式
            cookieInput.addEventListener('input', Throttle.debounce(() => {
                this.validateCookieFormat(cookieInput.value);
            }, 500));

            // 粘贴时自动验证
            cookieInput.addEventListener('paste', () => {
                setTimeout(() => {
                    this.validateCookieFormat(cookieInput.value);
                }, 100);
            });
        }

        if (validateBtn) {
            validateBtn.addEventListener('click', () => {
                this.validateCookie();
            });
        }

        if (saveCookieBtn) {
            saveCookieBtn.addEventListener('click', () => {
                this.saveCookie();
            });
        }

        if (loadCookieBtn) {
            loadCookieBtn.addEventListener('click', () => {
                this.showCookieSelector();
            });
        }
    }

    validateCookieFormat(cookieString) {
        const statusElement = document.getElementById('cookieStatus');
        if (!statusElement) return;

        if (!cookieString.trim()) {
            statusElement.className = 'cookie-status';
            statusElement.style.display = 'none';
            return;
        }

        const validation = Validator.validateCookie(cookieString);
        
        statusElement.className = `cookie-status ${validation.valid ? 'success' : 'error'}`;
        statusElement.innerHTML = `
            <i class="fas ${validation.valid ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            ${validation.message}
        `;
        statusElement.style.display = 'block';

        return validation.valid;
    }

    async validateCookie() {
        const cookieInput = document.getElementById('cookieInput');
        const cookieString = cookieInput.value.trim();

        if (!cookieString) {
            Toast.error('请输入Cookie');
            return false;
        }

        // 先进行本地格式验证
        if (!this.validateCookieFormat(cookieString)) {
            return false;
        }

        Loading.show('验证Cookie中...');

        try {
            const response = await ApiClient.post('/api/crawler/validate-cookie', {
                cookie_string: cookieString
            });

            if (response.success && response.valid) {
                this.currentCookie = cookieString;
                
                const statusElement = document.getElementById('cookieStatus');
                statusElement.className = 'cookie-status success';
                statusElement.innerHTML = `
                    <i class="fas fa-check-circle"></i>
                    ${response.message}
                    <div class="mt-1">
                        <small>
                            今日使用: ${response.usage_info.daily_usage}/${response.usage_info.max_daily_usage} 次
                            ${response.usage_info.last_used ? 
                                `| 上次使用: ${DateUtils.formatRelative(response.usage_info.last_used)}` : 
                                ''}
                        </small>
                    </div>
                `;

                Toast.success('Cookie验证成功');
                this.updateFormState();
                return true;
            } else {
                Toast.error(response.message || 'Cookie验证失败');
                return false;
            }
        } catch (error) {
            console.error('Cookie验证失败:', error);
            Toast.error('Cookie验证失败: ' + error.message);
            return false;
        } finally {
            Loading.hide();
        }
    }

    async saveCookie() {
        const cookieInput = document.getElementById('cookieInput');
        const cookieNameInput = document.getElementById('cookieName');
        
        const cookieString = cookieInput.value.trim();
        const cookieName = cookieNameInput.value.trim();

        if (!cookieString) {
            Toast.error('请输入Cookie');
            return;
        }

        if (!cookieName) {
            Toast.error('请输入Cookie名称');
            return;
        }

        // 验证Cookie格式
        if (!this.validateCookieFormat(cookieString)) {
            Toast.error('Cookie格式无效，请检查后重试');
            return;
        }

        Loading.show('保存Cookie中...');

        try {
            const response = await ApiClient.post('/api/config/cookies', {
                name: cookieName,
                cookie_string: cookieString
            });

            if (response.success) {
                Toast.success(response.message);
                cookieNameInput.value = '';
                this.loadCookieList(); // 重新加载Cookie列表
            } else {
                Toast.error(response.error || '保存Cookie失败');
            }
        } catch (error) {
            console.error('保存Cookie失败:', error);
            Toast.error('保存Cookie失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    async loadCookieList() {
        try {
            const response = await ApiClient.get('/api/config/cookies');
            
            if (response.success) {
                this.cookieList = response.data;
                this.renderCookieList();
            }
        } catch (error) {
            console.error('加载Cookie列表失败:', error);
        }
    }

    renderCookieList() {
        const listContainer = document.getElementById('cookieList');
        if (!listContainer) return;

        DOMUtils.empty(listContainer);

        if (this.cookieList.length === 0) {
            listContainer.innerHTML = '<div class="text-muted text-center">暂无保存的Cookie</div>';
            return;
        }

        this.cookieList.forEach(cookie => {
            const cookieItem = DOMUtils.createElement('div', 'cookie-item');
            
            if (!cookie.can_use) {
                cookieItem.classList.add('unavailable');
            }

            const statusIcon = cookie.can_use ? 
                '<i class="fas fa-check-circle text-success"></i>' : 
                '<i class="fas fa-exclamation-triangle text-warning"></i>';

            cookieItem.innerHTML = `
                ${statusIcon}
                <span class="cookie-name">${cookie.name}</span>
                <span class="cookie-usage">(${cookie.daily_usage}/2)</span>
                <button class="remove-btn" onclick="cookieManager.deleteCookie('${cookie.name}')" 
                        title="删除Cookie">
                    <i class="fas fa-times"></i>
                </button>
            `;

            // 点击加载Cookie
            cookieItem.addEventListener('click', (e) => {
                if (e.target.classList.contains('remove-btn') || 
                    e.target.closest('.remove-btn')) {
                    return;
                }
                this.loadCookie(cookie.name);
            });

            listContainer.appendChild(cookieItem);
        });
    }

    async loadCookie(cookieName) {
        Loading.show('加载Cookie中...');

        try {
            // 从后端API加载Cookie
            const response = await ApiClient.get(`/api/config/cookies/${cookieName}`);
            
            if (response.success && response.data) {
                const cookieInput = document.getElementById('cookieInput');
                cookieInput.value = response.data.cookie_string;
                
                // 验证加载的Cookie
                await this.validateCookie();
                Toast.success(`Cookie "${cookieName}" 加载成功`);
            } else {
                Toast.error(response.error || 'Cookie加载失败');
            }
        } catch (error) {
            console.error('加载Cookie失败:', error);
            Toast.error('加载Cookie失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    async deleteCookie(cookieName) {
        if (!confirm(`确定要删除Cookie "${cookieName}" 吗？`)) {
            return;
        }

        Loading.show('删除Cookie中...');

        try {
            const response = await ApiClient.delete(`/api/config/cookies/${cookieName}`);
            
            if (response.success) {
                Toast.success(response.message);
                this.loadCookieList(); // 重新加载列表
            } else {
                Toast.error(response.error || '删除Cookie失败');
            }
        } catch (error) {
            console.error('删除Cookie失败:', error);
            Toast.error('删除Cookie失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    showCookieSelector() {
        if (this.cookieList.length === 0) {
            Toast.info('暂无保存的Cookie，请先保存一些Cookie');
            return;
        }

        // 显示Cookie选择对话框
        this.loadCookieList();
    }

    async checkCookieRestrictions(city, categories) {
        if (!this.currentCookie) {
            return {
                can_use: false,
                error_messages: ['请先验证Cookie']
            };
        }

        try {
            const response = await ApiClient.post('/api/crawler/check-restrictions', {
                cookie_string: this.currentCookie,
                city: city,
                categories: categories
            });

            if (response.success) {
                return response.data;
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            console.error('检查Cookie限制失败:', error);
            throw error;
        }
    }

    updateFormState() {
        // 通知主应用更新表单状态
        if (window.app && window.app.updateFormState) {
            window.app.updateFormState();
        }
    }

    getCurrentCookie() {
        return this.currentCookie;
    }

    isValidCookie() {
        return !!this.currentCookie;
    }
}

// 创建全局Cookie管理器实例
window.cookieManager = new CookieManager();