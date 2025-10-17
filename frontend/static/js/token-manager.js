/**
 * API Token管理器
 * 处理第三方API Token的存储、验证和管理功能
 */

class ApiTokenManager {
    constructor() {
        this.tokens = this.loadTokens();
        this.currentToken = null;
        this.initElements();
        this.bindEvents();
    }

    initElements() {
        // Token输入相关元素
        this.tokenNameInput = document.getElementById('tokenName');
        this.tokenValueInput = document.getElementById('tokenValue');
        this.saveTokenBtn = document.getElementById('saveTokenBtn');
        this.tokenStatus = document.getElementById('tokenStatus');
        
        // Token列表相关元素
        this.tokenList = document.getElementById('tokenList');
    }

    bindEvents() {
        // 保存Token按钮事件
        if (this.saveTokenBtn) {
            this.saveTokenBtn.addEventListener('click', () => {
                this.saveCurrentToken();
            });
        }

        // Token输入变化事件
        if (this.tokenNameInput && this.tokenValueInput) {
            [this.tokenNameInput, this.tokenValueInput].forEach(input => {
                input.addEventListener('input', () => {
                    this.hideTokenStatus();
                });
            });
        }
    }

    // 加载所有保存的token
    loadTokens() {
        const saved = localStorage.getItem('api_tokens');
        return saved ? JSON.parse(saved) : {};
    }

    // 保存token到本地存储
    saveToken(name, token) {
        if (!name || !token) {
            this.showTokenStatus('Token名称和值都不能为空', 'error');
            return false;
        }

        this.tokens[name] = {
            token: token,
            savedAt: new Date().toISOString(),
            lastUsed: new Date().toISOString()
        };

        localStorage.setItem('api_tokens', JSON.stringify(this.tokens));
        this.showTokenStatus(`Token "${name}" 已保存`, 'success');
        this.renderTokenList();
        return true;
    }

    // 从本地存储获取token
    getToken(name) {
        const tokenData = this.tokens[name];
        if (tokenData) {
            // 更新最后使用时间
            tokenData.lastUsed = new Date().toISOString();
            localStorage.setItem('api_tokens', JSON.stringify(this.tokens));
            return tokenData.token;
        }
        return null;
    }

    // 删除token
    removeToken(name) {
        delete this.tokens[name];
        localStorage.setItem('api_tokens', JSON.stringify(this.tokens));
        this.showTokenStatus(`Token "${name}" 已删除`, 'info');
        this.renderTokenList();
        
        // 如果删除的是当前token，清除当前token
        if (this.currentToken === name) {
            this.currentToken = null;
            ApiClient.setDefaultAuthHeader(null);
        }
    }

    // 设置当前token
    setCurrentToken(name) {
        const token = this.getToken(name);
        if (!token) {
            this.showTokenStatus(`Token "${name}" 不存在`, 'error');
            return false;
        }

        this.currentToken = name;
        
        // 设置默认Authorization header
        if (window.ApiClient) {
            ApiClient.setDefaultAuthHeader(`Bearer ${token}`);
        }
        
        this.showTokenStatus(`已切换到Token "${name}"`, 'success');
        this.updateTokenListUI();
        return true;
    }

    // 验证token有效性
    async validateToken(name) {
        const token = this.getToken(name);
        if (!token) {
            return { valid: false, message: 'Token不存在' };
        }

        try {
            this.showTokenStatus('正在验证Token...', 'info');
            
            const response = await fetch('/api/test/validate-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.showTokenStatus('Token验证成功', 'success');
                return { valid: true, message: 'Token有效' };
            } else {
                const result = await response.json();
                this.showTokenStatus(result.message || 'Token验证失败', 'error');
                return { valid: false, message: result.message || 'Token验证失败' };
            }
        } catch (error) {
            console.error('Token验证失败:', error);
            this.showTokenStatus('Token验证失败，请检查网络连接', 'error');
            return { valid: false, message: 'Token验证失败，请检查网络连接' };
        }
    }

    // 获取token列表
    getTokenList() {
        return Object.keys(this.tokens).map(name => ({
            name,
            ...this.tokens[name]
        }));
    }

    // 保存当前输入的token
    saveCurrentToken() {
        const name = this.tokenNameInput.value.trim();
        const token = this.tokenValueInput.value.trim();

        if (this.saveToken(name, token)) {
            // 清空输入框
            this.tokenNameInput.value = '';
            this.tokenValueInput.value = '';
        }
    }

    // 显示token状态信息
    showTokenStatus(message, type = 'info') {
        if (this.tokenStatus) {
            this.tokenStatus.textContent = message;
            this.tokenStatus.className = `token-status show ${type}`;
        }
    }

    // 隐藏token状态信息
    hideTokenStatus() {
        if (this.tokenStatus) {
            this.tokenStatus.className = 'token-status';
        }
    }

    // 渲染token列表
    renderTokenList() {
        if (!this.tokenList) return;

        const tokens = this.getTokenList();
        
        if (tokens.length === 0) {
            this.tokenList.innerHTML = '<div class="text-muted text-center p-3">暂无保存的Token</div>';
            return;
        }

        this.tokenList.innerHTML = tokens.map(tokenData => {
            const isCurrent = this.currentToken === tokenData.name;
            const lastUsed = new Date(tokenData.lastUsed).toLocaleString('zh-CN');
            
            return `
                <div class="token-item" data-token-name="${tokenData.name}">
                    <div class="token-info">
                        <span class="token-name">${tokenData.name}</span>
                        <span class="token-meta">最后使用: ${lastUsed}</span>
                        ${isCurrent ? '<span class="token-current-badge">当前使用</span>' : ''}
                    </div>
                    <div class="token-actions">
                        <button class="btn btn-sm ${isCurrent ? 'btn-success' : 'btn-outline-primary'} use-token-btn" 
                                onclick="apiTokenManager.setCurrentToken('${tokenData.name}')"
                                title="${isCurrent ? '正在使用' : '使用此Token'}">
                            <i class="fas ${isCurrent ? 'fa-check' : 'fa-check'}"></i>
                            ${isCurrent ? '使用中' : '使用'}
                        </button>
                        <button class="btn btn-sm btn-outline-warning validate-token-btn" 
                                onclick="apiTokenManager.validateToken('${tokenData.name}')"
                                title="验证Token有效性">
                            <i class="fas fa-shield-alt"></i>
                            验证
                        </button>
                        <button class="btn btn-sm btn-outline-danger remove-token-btn" 
                                onclick="apiTokenManager.removeToken('${tokenData.name}')"
                                title="删除Token">
                            <i class="fas fa-trash"></i>
                            删除
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 更新token列表UI状态
    updateTokenListUI() {
        this.renderTokenList();
    }

    // 获取当前有效的token
    getCurrentValidToken() {
        if (!this.currentToken) {
            return null;
        }
        
        const token = this.getToken(this.currentToken);
        return token ? { name: this.currentToken, token } : null;
    }

    // 自动选择最适合的token
    async autoSelectBestToken() {
        const tokens = this.getTokenList();
        
        // 按最后使用时间排序
        tokens.sort((a, b) => new Date(b.lastUsed) - new Date(a.lastUsed));
        
        for (const tokenData of tokens) {
            const validation = await this.validateToken(tokenData.name);
            if (validation.valid) {
                this.setCurrentToken(tokenData.name);
                return { name: tokenData.name, token: tokenData.token };
            }
        }
        
        return null;
    }

    // 为API请求添加认证头
    addAuthHeader(options = {}) {
        const currentToken = this.getCurrentValidToken();
        if (currentToken) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${currentToken.token}`;
        }
        return options;
    }

    // 显示token管理模态框
    showTokenModal() {
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.innerHTML = `
            <div class="modal-content modal-lg">
                <div class="modal-header">
                    <h3><i class="fas fa-key"></i> API Token管理</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="token-management-section">
                        <h4><i class="fas fa-plus"></i> 添加新Token</h4>
                        <div class="token-input-group">
                            <div class="input-group">
                                <input type="text" id="modalTokenName" class="form-control form-control-sm" 
                                       placeholder="Token名称 (如: production, test)">
                                <input type="password" id="modalTokenValue" class="form-control form-control-sm" 
                                       placeholder="请输入API Token">
                                <button class="btn btn-primary btn-sm" id="modalSaveTokenBtn">
                                    <i class="fas fa-save"></i> 保存
                                </button>
                            </div>
                            <div class="token-status" id="modalTokenStatus"></div>
                        </div>
                    </div>
                    
                    <div class="token-management-section">
                        <h4><i class="fas fa-list"></i> 已保存的Token</h4>
                        <div class="token-list" id="modalTokenList">
                            <!-- Token列表将在这里渲染 -->
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">关闭</button>
                    <button class="btn btn-primary" onclick="apiTokenManager.refreshTokenList()">刷新列表</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 初始化模态框中的事件
        this.initModalEvents(modal);
        
        // 渲染token列表
        this.renderModalTokenList(modal);
    }

    // 初始化模态框事件
    initModalEvents(modal) {
        const saveBtn = modal.querySelector('#modalSaveTokenBtn');
        const nameInput = modal.querySelector('#modalTokenName');
        const valueInput = modal.querySelector('#modalTokenValue');
        const statusDiv = modal.querySelector('#modalTokenStatus');
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const name = nameInput.value.trim();
                const token = valueInput.value.trim();
                
                if (this.saveToken(name, token)) {
                    nameInput.value = '';
                    valueInput.value = '';
                    this.renderModalTokenList(modal);
                }
            });
        }
        
        // 输入框变化事件
        [nameInput, valueInput].forEach(input => {
            input.addEventListener('input', () => {
                if (statusDiv) {
                    statusDiv.className = 'token-status';
                }
            });
        });
    }

    // 渲染模态框中的token列表
    renderModalTokenList(modal) {
        const tokenList = modal.querySelector('#modalTokenList');
        if (!tokenList) return;

        const tokens = this.getTokenList();
        
        if (tokens.length === 0) {
            tokenList.innerHTML = '<div class="text-muted text-center p-3">暂无保存的Token</div>';
            return;
        }

        tokenList.innerHTML = tokens.map(tokenData => {
            const isCurrent = this.currentToken === tokenData.name;
            const lastUsed = new Date(tokenData.lastUsed).toLocaleString('zh-CN');
            
            return `
                <div class="token-item" data-token-name="${tokenData.name}">
                    <div class="token-info">
                        <span class="token-name">${tokenData.name}</span>
                        <span class="token-meta">最后使用: ${lastUsed}</span>
                        ${isCurrent ? '<span class="token-current-badge">当前使用</span>' : ''}
                    </div>
                    <div class="token-actions">
                        <button class="btn btn-sm ${isCurrent ? 'btn-success' : 'btn-outline-primary'} use-token-btn" 
                                onclick="apiTokenManager.setCurrentToken('${tokenData.name}'); apiTokenManager.renderModalTokenList(document.querySelector('.modal.show'));">
                            <i class="fas ${isCurrent ? 'fa-check' : 'fa-check'}"></i>
                            ${isCurrent ? '使用中' : '使用'}
                        </button>
                        <button class="btn btn-sm btn-outline-warning validate-token-btn" 
                                onclick="apiTokenManager.validateToken('${tokenData.name}')">
                            <i class="fas fa-shield-alt"></i>
                            验证
                        </button>
                        <button class="btn btn-sm btn-outline-danger remove-token-btn" 
                                onclick="apiTokenManager.removeToken('${tokenData.name}'); apiTokenManager.renderModalTokenList(document.querySelector('.modal.show'));">
                            <i class="fas fa-trash"></i>
                            删除
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 刷新token列表
    refreshTokenList() {
        this.renderTokenList();
        const modal = document.querySelector('.modal.show');
        if (modal) {
            this.renderModalTokenList(modal);
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    window.apiTokenManager = new ApiTokenManager();
});