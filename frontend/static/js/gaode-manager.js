/**
 * 高德API管理器
 * 处理高德API Key验证、文件上传和电话查询功能
 */

class GaodeManager {
    constructor() {
        this.apiKey = '';
        this.currentFile = null;
        this.processTaskId = null;
        this.isApiKeyValid = false;
        this.uploadedFiles = []; // 存储从上传模块传递的文件
        
        this.initElements();
        this.bindEvents();
        this.loadSavedApiKey(); // 加载保存的API密钥
    }
    
    initElements() {
        // API Key相关元素
        this.apiKeyInput = document.getElementById('gaodeApiKey');
        this.toggleApiKeyBtn = document.getElementById('toggleApiKeyBtn');
        this.apiKeyStatus = document.getElementById('apiKeyStatus');
        
        // 文件上传相关元素
        this.fileInput = document.getElementById('gaodeFileInput');
        this.fileInfo = document.getElementById('gaodeFileInfo');
        
        // 处理相关元素
        this.processBtn = document.getElementById('processGaodeBtn');
        this.progressContainer = document.getElementById('gaodeProgress');
        this.progressLabel = document.getElementById('gaodeProgressLabel');
        this.progressPercentage = document.getElementById('gaodeProgressPercentage');
        this.progressBar = document.getElementById('gaodeProgressBar');
        
        // 结果相关元素
        this.resultContainer = document.getElementById('gaodeResult');
        this.resultInfo = document.getElementById('gaodeResultInfo');
        this.downloadResultBtn = document.getElementById('downloadGaodeResultBtn');
    }
    
    bindEvents() {
        // API Key显示/隐藏切换
        this.toggleApiKeyBtn.addEventListener('click', () => {
            this.toggleApiKeyVisibility();
        });
        
        // API Key输入变化
        this.apiKeyInput.addEventListener('input', () => {
            this.onApiKeyChange();
        });
        
        // 文件选择
        this.fileInput.addEventListener('change', () => {
            this.onFileSelect();
        });
        
        // 开始处理
        this.processBtn.addEventListener('click', () => {
            this.startProcessing();
        });
        
        // 下载结果
        this.downloadResultBtn.addEventListener('click', () => {
            this.downloadResult();
        });
    }
    
    toggleApiKeyVisibility() {
        const isPassword = this.apiKeyInput.type === 'password';
        this.apiKeyInput.type = isPassword ? 'text' : 'password';
        
        const icon = this.toggleApiKeyBtn.querySelector('i');
        icon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
    }
    
    async onApiKeyChange() {
        this.apiKey = this.apiKeyInput.value.trim();
        this.hideApiKeyStatus();
        this.isApiKeyValid = false;
        
        if (this.apiKey.length > 0) {
            // 验证API key
            await this.validateApiKey();
            // 保存API密钥到本地存储
            this.saveApiKey();
        } else {
            // 清空本地存储的API密钥
            this.clearSavedApiKey();
        }
        
        this.updateFileInputState();
        this.updateProcessButtonState();
    }
    

    
    showApiKeyStatus(message, type) {
        this.apiKeyStatus.textContent = message;
        this.apiKeyStatus.className = `api-key-status ${type}`;
    }
    
    hideApiKeyStatus() {
        this.apiKeyStatus.className = 'api-key-status';
    }
    
    async validateApiKey() {
        if (!this.apiKey) {
            this.isApiKeyValid = false;
            return;
        }
        
        try {
            this.showApiKeyStatus('验证中...', 'info');
            
            const response = await fetch('/api/gaode/validate_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: this.apiKey
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.isApiKeyValid = true;
                this.showApiKeyStatus('API Key 有效', 'success');
            } else {
                this.isApiKeyValid = false;
                this.showApiKeyStatus(result.message || 'API Key 无效', 'error');
            }
        } catch (error) {
            console.error('验证API Key失败:', error);
            this.isApiKeyValid = false;
            this.showApiKeyStatus('验证失败，请检查网络连接', 'error');
        }
    }
    
    updateFileInputState() {
        this.fileInput.disabled = false;
    }
    
    updateProcessButtonState() {
        this.processBtn.disabled = !this.isApiKeyValid || !this.currentFile;
    }
    
    onFileSelect() {
        const file = this.fileInput.files[0];
        
        if (!file) {
            this.currentFile = null;
            this.hideFileInfo();
            this.updateProcessButtonState();
            return;
        }
        
        // 验证文件类型
        if (!file.name.toLowerCase().endsWith('.csv')) {
            this.showFileInfo('请选择CSV格式的文件', 'error');
            this.fileInput.value = '';
            this.currentFile = null;
            this.updateProcessButtonState();
            return;
        }
        
        // 验证文件大小 (最大10MB)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showFileInfo('文件大小不能超过10MB', 'error');
            this.fileInput.value = '';
            this.currentFile = null;
            this.updateProcessButtonState();
            return;
        }
        
        this.currentFile = file;
        this.showFileInfo(`已选择文件: ${file.name} (${this.formatFileSize(file.size)})`, 'success');
        this.updateProcessButtonState();
    }
    
    showFileInfo(message, type = 'info') {
        this.fileInfo.textContent = message;
        this.fileInfo.className = `file-info show ${type}`;
    }
    
    hideFileInfo() {
        this.fileInfo.className = 'file-info';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async startProcessing() {
        if (!this.isApiKeyValid || !this.currentFile) {
            return;
        }
        
        try {
            // 准备FormData
            const formData = new FormData();
            formData.append('file', this.currentFile);
            formData.append('api_key', this.apiKey);
            
            // 显示进度
            this.showProgress();
            this.processBtn.disabled = true;
            
            // 上传文件并开始处理
            const response = await fetch('/api/gaode/upload_and_query', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 同步处理完成，直接显示结果
                this.hideProgress();
                this.processBtn.disabled = false;
                
                // 显示处理结果
                this.showResult(result.output_filename, result.message);
                showToast(result.message, 'success');
            } else {
                this.hideProgress();
                this.processBtn.disabled = false;
                showToast(result.error || '处理失败', 'error');
            }
        } catch (error) {
            console.error('处理错误:', error);
            this.hideProgress();
            this.processBtn.disabled = false;
            showToast('处理过程中发生错误', 'error');
        }
    }
    

    
    showProgress() {
        this.progressContainer.style.display = 'block';
        this.resultContainer.style.display = 'none';
    }
    
    hideProgress() {
        this.progressContainer.style.display = 'none';
    }
    
    updateProgress(percentage, message) {
        this.progressLabel.textContent = message;
        this.progressPercentage.textContent = `${Math.round(percentage)}%`;
        this.progressBar.style.width = `${percentage}%`;
    }
    
    showResult(resultFile, message) {
        this.resultInfo.textContent = message;
        this.downloadResultBtn.setAttribute('data-file', resultFile);
        this.resultContainer.style.display = 'block';
    }
    
    async downloadResult() {
        const resultFile = this.downloadResultBtn.getAttribute('data-file');
        
        if (!resultFile) {
            showToast('没有可下载的结果文件', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/gaode/download/${encodeURIComponent(resultFile)}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = resultFile;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                showToast('文件下载成功', 'success');
            } else {
                showToast('文件下载失败', 'error');
            }
        } catch (error) {
            console.error('下载错误:', error);
            showToast('下载过程中发生错误', 'error');
        }
    }

    // 新增：从文件上传模块接收文件
    setUploadedFiles(files) {
        this.uploadedFiles = files || [];
        this.updateFileInputState();
        this.updateProcessButtonState();
        
        if (this.uploadedFiles.length > 0) {
            Toast.info(`已接收 ${this.uploadedFiles.length} 个文件，可以进行高德电话查询`);
            // 自动选择第一个CSV文件
            this.autoSelectFirstFile();
        }
    }

    // 新增：获取可用的CSV文件列表
    getAvailableFiles() {
        const files = [];
        
        // 从上传模块获取文件
        if (this.uploadedFiles.length > 0) {
            this.uploadedFiles.forEach(file => {
                if (file.name.toLowerCase().endsWith('.csv')) {
                    files.push({
                        name: file.name,
                        size: file.size,
                        source: 'upload',
                        file: file
                    });
                }
            });
        }

        return files;
    }

    // 新增：显示可用文件选择界面
    showFileSelection() {
        const availableFiles = this.getAvailableFiles();
        
        if (availableFiles.length === 0) {
            Toast.warning('没有可用的CSV文件，请先上传文件');
            return;
        }

        // 创建文件选择界面
        const selectionHtml = availableFiles.map((file, index) => `
            <div class="file-selection-item" data-index="${index}">
                <input type="radio" name="gaodeFileSelect" value="${index}" id="file_${index}">
                <label for="file_${index}">
                    <strong>${file.name}</strong>
                    <span class="file-meta">${this.formatFileSize(file.size)}</span>
                    <span class="file-source">来源: ${file.source === 'upload' ? '上传' : '爬虫'}</span>
                </label>
            </div>
        `).join('');

        // 创建模态框显示文件选择
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3><i class="fas fa-file-csv"></i> 选择要处理的文件</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="file-selection-list">
                        ${selectionHtml}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                    <button class="btn btn-primary" onclick="gaodeManager.confirmFileSelection()">确认选择</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    // 新增：确认文件选择
    confirmFileSelection() {
        const selectedRadio = document.querySelector('input[name="gaodeFileSelect"]:checked');
        if (!selectedRadio) {
            Toast.warning('请选择一个文件');
            return;
        }

        const fileIndex = parseInt(selectedRadio.value);
        const selectedFile = this.getAvailableFiles()[fileIndex];
        
        if (selectedFile) {
            this.currentFile = selectedFile.file;
            this.showFileInfo(`已选择文件: ${selectedFile.name} (${this.formatFileSize(selectedFile.size)})`, 'success');
            this.updateProcessButtonState();
        }

        // 关闭模态框
        const modal = document.querySelector('.modal.show');
        if (modal) {
            modal.remove();
        }
    }

    // 新增：自动选择第一个可用的CSV文件
    autoSelectFirstFile() {
        const availableFiles = this.getAvailableFiles();
        if (availableFiles.length > 0) {
            this.currentFile = availableFiles[0].file;
            this.showFileInfo(`自动选择文件: ${availableFiles[0].name}`, 'info');
            this.updateProcessButtonState();
            return true;
        }
        return false;
    }

    // API密钥本地存储功能
    saveApiKey() {
        try {
            localStorage.setItem('gaode_api_key', this.apiKey);
        } catch (error) {
            console.warn('无法保存API密钥到本地存储:', error);
        }
    }

    loadSavedApiKey() {
        try {
            const savedApiKey = localStorage.getItem('gaode_api_key');
            if (savedApiKey) {
                this.apiKeyInput.value = savedApiKey;
                this.apiKey = savedApiKey;
                // 自动验证保存的API密钥
                this.validateApiKey();
            }
        } catch (error) {
            console.warn('无法从本地存储加载API密钥:', error);
        }
    }

    clearSavedApiKey() {
        try {
            localStorage.removeItem('gaode_api_key');
        } catch (error) {
            console.warn('无法清除本地存储的API密钥:', error);
        }
    }
}

// 全局实例
let gaodeManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    gaodeManager = new GaodeManager();
});