/**
 * 第三方API管理器
 * 处理文件上传到第三方平台和AI品牌数据导入功能
 */

class ThirdPartyApiManager {
    constructor() {
        this.currentEnvironment = 'test';
        this.apiBaseUrl = '/api/third-party';
        this.currentTaskId = null;
        this.pollInterval = null;
        this.currentToken = '';
        this.selectedFile = null;
        this.initElements();
        this.bindEvents();
        this.initTokenValidation();
        this.loadSavedToken(); // 加载保存的token
        this.loadSavedEnvironment(); // 加载保存的环境设置
    }

    initElements() {
        // 文件导入上传相关元素
        this.thirdPartySection = document.getElementById('thirdPartySection');
        this.thirdPartyFileInput = document.getElementById('thirdPartyFileInput');
        this.thirdPartyStatus = document.getElementById('thirdPartyStatus');
        this.thirdPartyProgress = document.getElementById('thirdPartyProgress');
        this.taskStatusContainer = document.getElementById('taskStatusContainer');
        this.environmentSelect = document.getElementById('environmentSelect');
        this.selectedFilesList = document.getElementById('selectedFilesList');
        this.filesList = document.getElementById('filesList');
    }

    bindEvents() {
        // 文件选择事件 - 选择后自动上传
        if (this.thirdPartyFileInput) {
            this.thirdPartyFileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e);
            });
        }

        // 环境切换事件
        if (this.environmentSelect) {
            this.environmentSelect.addEventListener('change', () => {
                this.currentEnvironment = this.environmentSelect.value;
                this.updateEnvironmentInfo();
                this.saveEnvironment(); // 保存环境设置
                this.reset(); // 重置状态
            });
        }
    }

    initTokenValidation() {
        const tokenInput = document.getElementById('apiTokenInput');
        const toggleBtn = document.getElementById('toggleTokenBtn');
        
        if (tokenInput) {
            tokenInput.addEventListener('input', (e) => {
                this.currentToken = e.target.value.trim();
                this.validateToken();
                this.updateControlsState();
                this.saveToken(); // 自动保存token
            });
        }
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleTokenVisibility();
            });
        }
    }
    
    validateToken() {
        const tokenStatus = document.getElementById('tokenInputStatus');
        if (!tokenStatus) return;
        
        if (this.currentToken.length === 0) {
            tokenStatus.textContent = '';
            tokenStatus.className = 'token-status';
        } else if (this.currentToken.length < 10) {
            tokenStatus.textContent = 'Token长度不足';
            tokenStatus.className = 'token-status invalid';
        } else {
            tokenStatus.textContent = 'Token格式正确';
            tokenStatus.className = 'token-status valid';
        }
    }
    
    toggleTokenVisibility() {
        const tokenInput = document.getElementById('apiTokenInput');
        const toggleBtn = document.getElementById('toggleTokenBtn');
        const icon = toggleBtn.querySelector('i');
        
        if (tokenInput.type === 'password') {
            tokenInput.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            tokenInput.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }
    
    updateControlsState() {
        const hasValidToken = this.currentToken.length >= 10;
        
        if (this.thirdPartyFileInput) {
            this.thirdPartyFileInput.disabled = !hasValidToken;
        }
    }

    handleFileSelection(event) {
        const files = Array.from(event.target.files);
        if (files.length > 0) {
            this.selectedFiles = files;
            
            // 验证所有文件格式
            const allowedTypes = ['.xlsx', '.xls'];
            const invalidFiles = files.filter(file => {
                const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
                return !allowedTypes.includes(fileExtension);
            });
            
            if (invalidFiles.length > 0) {
                this.showStatus(`不支持的文件格式：${invalidFiles.map(f => f.name).join(', ')}，请选择Excel文件(.xls, .xlsx)`, 'error');
                this.thirdPartyFileInput.value = '';
                this.selectedFiles = null;
                this.updateControlsState();
                this.hideSelectedFilesList();
                return;
            }
            
            // 检查token
            if (!this.currentToken || this.currentToken.length < 10) {
                this.showStatus('请先输入有效的API Token', 'error');
                this.thirdPartyFileInput.value = '';
                this.selectedFiles = null;
                this.hideSelectedFilesList();
                return;
            }
            
            // 显示已选择的文件列表
            this.showSelectedFilesList();
            this.showStatus(`已选择 ${files.length} 个文件`, 'info');
            
            // 更新控件状态
            this.updateControlsState();

            // 自动开始上传和导入流程
            this.handleThirdPartyUpload();
        } else {
            this.selectedFiles = null;
            this.hideSelectedFilesList();
            this.updateControlsState();
        }
    }

    async handleThirdPartyUpload() {
        try {
            const files = this.thirdPartyFileInput?.files;
            if (!files || files.length === 0) {
                this.showStatus('请先选择文件', 'error');
                return;
            }

            // 检查token
            if (!this.currentToken || this.currentToken.length < 10) {
                this.showStatus('请先输入有效的API Token', 'error');
                return;
            }

            // 显示上传进度
            this.showProgress('正在上传文件到第三方平台...');
            this.thirdPartyFileInput.disabled = true;

            // 获取环境设置
            const environment = this.environmentSelect?.value || 'test';
            const uploadEndpoint = environment === 'production' ? '/production/upload' : '/test/upload';

            // 上传所有文件
            const fileIds = [];
            const uploadResults = [];
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                this.updateFileStatus(i, '上传中...', 'bg-warning');
                
                try {
                    const uploadResult = await this.uploadFile(file, uploadEndpoint, this.currentToken);
                    
                    if (uploadResult.code === 0) {
                        fileIds.push(uploadResult.data.fileId);
                        uploadResults.push(uploadResult);
                        this.updateFileStatus(i, '上传成功', 'bg-success');
                        this.showStatus(`文件 ${file.name} 上传成功，文件ID: ${uploadResult.data.fileId}`, 'success');
                    } else {
                        this.updateFileStatus(i, '上传失败', 'bg-danger');
                        console.error(`文件 ${file.name} 上传失败:`, uploadResult);
                        throw new Error(uploadResult.msg || '文件上传失败');
                    }
                } catch (error) {
                    this.updateFileStatus(i, '上传失败', 'bg-danger');
                    throw error;
                }
                
                // 文件间添加延迟，避免请求过于频繁
                if (i < files.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            // 检查是否有文件上传成功
            if (fileIds.length === 0) {
                throw new Error('没有文件上传成功');
            }

            // 添加延迟等待第三方系统处理文件
            this.showProgress('所有文件上传成功，等待系统处理...');
            console.log('等待3秒后开始数据导入，确保第三方系统已处理文件');
            await new Promise(resolve => setTimeout(resolve, 3000));

            // 自动开始数据导入
            console.log('开始启动数据导入，fileIds:', fileIds);
            await this.startDataImport(fileIds, environment, this.currentToken);

        } catch (error) {
            console.error('第三方API上传失败:', error);
            this.showStatus(`上传失败: ${error.message}`, 'error');
        } finally {
            this.thirdPartyFileInput.disabled = false;
            this.hideProgress();
        }
    }

    async uploadFile(file, endpoint, token) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('busSubType', '1001');

        const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'token': token
            },
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ msg: '网络错误' }));
            throw new Error(errorData.msg || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    async startDataImport(fileIds, environment, token) {
        try {
            console.log('开始数据导入流程，参数:', { fileIds, environment, token: token.substring(0, 10) + '...' });
            this.showProgress('正在启动数据导入任务...');
            
            const endpoint = environment === 'production' ? '/production/import' : '/test/import';
            console.log('使用导入端点:', endpoint);
            
            const requestBody = {
                fileIds: fileIds
            };
            console.log('发送导入请求，请求体:', requestBody);
            
            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'token': token
                },
                body: JSON.stringify(requestBody)
            });

            console.log('导入接口响应状态:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ msg: '网络错误' }));
                console.error('导入接口返回错误:', errorData);
                throw new Error(errorData.msg || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('导入接口响应数据:', result);
            
            if (result.code === 0) {
                this.currentTaskId = result.data; // data直接是taskId字符串
                console.log('数据导入任务启动成功，任务ID:', this.currentTaskId);
                this.showStatus(`数据导入任务已启动，任务ID: ${this.currentTaskId}`, 'success');
                
                // 暂时停止轮询任务状态，因为接口还未完善
                console.log('任务状态查询接口暂未完善，停止轮询');
                this.showStatus(`任务已启动，共导入 ${fileIds.length} 个文件，请手动查看任务状态`, 'info');
                
                // 开始轮询任务状态（已注释）
                // this.startTaskPolling(environment, token);
            } else {
                console.error('导入任务启动失败，错误信息:', result.msg);
                throw new Error(result.msg || '启动导入任务失败');
            }

        } catch (error) {
            console.error('启动数据导入失败，详细错误:', error);
            this.showStatus(`启动导入失败: ${error.message}`, 'error');
        }
    }

    startTaskPolling(environment, token) {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        this.pollInterval = setInterval(async () => {
            try {
                await this.checkTaskStatus(environment, token);
            } catch (error) {
                console.error('查询任务状态失败:', error);
                this.stopTaskPolling();
                this.showStatus(`查询任务状态失败: ${error.message}`, 'error');
            }
        }, 3000); // 每3秒查询一次
    }

    async checkTaskStatus(environment, token) {
        if (!this.currentTaskId) return;

        const endpoint = environment === 'production' ? '/production/task/status' : '/test/task/status';
        
        const response = await fetch(`${this.apiBaseUrl}${endpoint}?taskId=${this.currentTaskId}`, {
            headers: {
                'token': token
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        
        if (result.code === 0) {
            this.updateTaskStatus(result.data);
            
            // 如果任务完成，停止轮询
            if (result.data.status === 'COMPLETED' || result.data.status === 'FAILED') {
                this.stopTaskPolling();
            }
        }
    }

    updateTaskStatus(taskData) {
        if (!this.taskStatusContainer) return;

        const statusHtml = `
            <div class="task-status-card">
                <h5><i class="fas fa-tasks"></i> 任务状态</h5>
                <div class="status-info">
                    <div class="status-item">
                        <span class="label">任务ID:</span>
                        <span class="value">${taskData.taskId}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">状态:</span>
                        <span class="value status-${taskData.status.toLowerCase()}">${this.getStatusText(taskData.status)}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">进度:</span>
                        <span class="value">${taskData.progress || 0}%</span>
                    </div>
                    <div class="status-item">
                        <span class="label">总数:</span>
                        <span class="value">${taskData.totalCount || 0}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">成功:</span>
                        <span class="value text-success">${taskData.successCount || 0}</span>
                    </div>
                    <div class="status-item">
                        <span class="label">失败:</span>
                        <span class="value text-danger">${taskData.failCount || 0}</span>
                    </div>
                </div>
                ${taskData.failDetails && taskData.failDetails.length > 0 ? this.renderFailDetails(taskData.failDetails) : ''}
            </div>
        `;

        this.taskStatusContainer.innerHTML = statusHtml;
        this.taskStatusContainer.style.display = 'block';
    }

    renderFailDetails(failDetails) {
        const detailsHtml = failDetails.map(detail => `
            <div class="fail-detail">
                <span class="row-index">第${detail.rowIndex}行:</span>
                <span class="brand-name">${detail.brandName}</span>
                <span class="fail-reason">${detail.failReason}</span>
            </div>
        `).join('');

        return `
            <div class="fail-details">
                <h6><i class="fas fa-exclamation-triangle"></i> 失败详情</h6>
                <div class="fail-list">${detailsHtml}</div>
            </div>
        `;
    }

    getStatusText(status) {
        const statusMap = {
            'PROCESSING': '处理中',
            'COMPLETED': '已完成',
            'FAILED': '失败',
            'PENDING': '等待中'
        };
        return statusMap[status] || status;
    }

    stopTaskPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    showStatus(message, type = 'info') {
        if (!this.thirdPartyStatus) return;

        const iconMap = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };

        this.thirdPartyStatus.innerHTML = `
            <div class="alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show" role="alert">
                <i class="${iconMap[type] || iconMap.info}"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        this.thirdPartyStatus.style.display = 'block';

        // 自动隐藏成功消息
        if (type === 'success') {
            setTimeout(() => {
                this.hideStatus();
            }, 5000);
        }
    }

    hideStatus() {
        if (this.thirdPartyStatus) {
            this.thirdPartyStatus.style.display = 'none';
        }
    }

    showProgress(message) {
        if (!this.thirdPartyProgress) return;

        this.thirdPartyProgress.innerHTML = `
            <div class="progress-container">
                <div class="progress-message">
                    <i class="fas fa-spinner fa-spin"></i>
                    ${message}
                </div>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 100%"></div>
                </div>
            </div>
        `;
        this.thirdPartyProgress.style.display = 'block';
    }

    hideProgress() {
        if (this.thirdPartyProgress) {
            this.thirdPartyProgress.style.display = 'none';
        }
    }

    updateEnvironmentInfo() {
        const environment = this.environmentSelect?.value || 'test';
        const infoText = environment === 'production'
            ? '生产环境 - 连接生产第三方API服务 (https://erqi.leyingiot.com)'
            : '测试环境 - 连接测试第三方API服务 (http://47.112.30.182:22402)';
        
        const envInfo = document.getElementById('environmentInfo');
        if (envInfo) {
            envInfo.textContent = infoText;
            envInfo.className = `environment-info ${environment}`;
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 保存token到本地存储
    saveToken() {
        if (this.currentToken) {
            localStorage.setItem('thirdPartyApiToken', this.currentToken);
        } else {
            localStorage.removeItem('thirdPartyApiToken');
        }
    }

    // 加载保存的token
    loadSavedToken() {
        const savedToken = localStorage.getItem('thirdPartyApiToken');
        if (savedToken) {
            this.currentToken = savedToken;
            const tokenInput = document.getElementById('apiTokenInput');
            if (tokenInput) {
                tokenInput.value = savedToken;
                this.validateToken();
                this.updateControlsState();
            }
        }
    }

    // 保存环境设置到本地存储
    saveEnvironment() {
        localStorage.setItem('thirdPartyEnvironment', this.currentEnvironment);
    }

    // 加载保存的环境设置
    loadSavedEnvironment() {
        const savedEnvironment = localStorage.getItem('thirdPartyEnvironment');
        if (savedEnvironment && this.environmentSelect) {
            this.currentEnvironment = savedEnvironment;
            this.environmentSelect.value = savedEnvironment;
            this.updateEnvironmentInfo();
        }
    }

    // 显示已选择的文件列表
    showSelectedFilesList() {
        if (!this.selectedFilesList || !this.filesList) return;
        
        const filesHtml = this.selectedFiles.map((file, index) => `
            <div class="file-item">
                <div class="file-info">
                    <i class="fas fa-file-excel"></i>
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">(${this.formatFileSize(file.size)})</span>
                </div>
                <div class="file-status" id="fileStatus${index}">
                    <span class="badge bg-secondary">等待上传</span>
                </div>
            </div>
        `).join('');
        
        this.filesList.innerHTML = filesHtml;
        this.selectedFilesList.style.display = 'block';
    }

    // 隐藏已选择的文件列表
    hideSelectedFilesList() {
        if (this.selectedFilesList) {
            this.selectedFilesList.style.display = 'none';
        }
    }

    // 更新单个文件状态
    updateFileStatus(index, status, className = '') {
        const statusElement = document.getElementById(`fileStatus${index}`);
        if (statusElement) {
            statusElement.innerHTML = `<span class="badge ${className}">${status}</span>`;
        }
    }

    // 重置所有状态
    reset() {
        this.stopTaskPolling();
        this.currentTaskId = null;
        this.hideStatus();
        this.hideProgress();
        this.hideSelectedFilesList();
        
        if (this.taskStatusContainer) {
            this.taskStatusContainer.style.display = 'none';
        }
        
        if (this.thirdPartyFileInput) {
            this.thirdPartyFileInput.value = '';
            this.thirdPartyFileInput.disabled = false;
        }
    }
}

// 全局实例
window.thirdPartyApiManager = new ThirdPartyApiManager();

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (window.thirdPartyApiManager) {
        window.thirdPartyApiManager.updateEnvironmentInfo();
    }
});