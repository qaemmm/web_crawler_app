/**
 * 文件上传管理器
 * 处理文件上传、进度显示和文件处理功能
 * 增加了Token验证功能
 */

class UploadManager {
    constructor() {
         this.uploadedFiles = [];
         this.isUploading = false;
         this.initElements();
         this.bindEvents();
     }
    
    initTokenValidation() {
        // Token验证功能已移至第三方API集成模块
        // 文件上传功能不再需要单独的Token验证
    }
    
    validateToken() {
        // Token验证功能已移至第三方API集成模块
    }
    
    toggleTokenVisibility() {
        // Token显示切换功能已移至第三方API集成模块
    }
    
    updateFileControlsState() {
        // 文件控制状态现在由第三方API集成模块管理
        const processBtn = document.getElementById('processUploadBtn');
        
        if (processBtn) {
            processBtn.disabled = this.uploadedFiles.length === 0;
        }
    }
    
    initElements() {
        // 文件上传相关元素
        this.uploadZone = document.getElementById('uploadZone');
        this.fileInput = document.getElementById('fileUploadInput');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.uploadProgressBar = document.getElementById('uploadProgressBar');
        this.uploadProgressLabel = document.getElementById('uploadProgressLabel');
        this.uploadProgressPercentage = document.getElementById('uploadProgressPercentage');
        this.uploadProgressDetails = document.getElementById('uploadProgressDetails');
        this.uploadFilesList = document.getElementById('uploadFilesList');
        this.processUploadBtn = document.getElementById('processUploadBtn');
        this.clearUploadBtn = document.getElementById('clearUploadBtn');
        this.manageTokenBtn = document.getElementById('manageTokenBtn');
    }
    
    bindEvents() {
        // 文件选择事件
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e.target.files);
            });
        }
        
        // 拖拽事件
        if (this.uploadZone) {
            this.uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.uploadZone.classList.add('drag-over');
            });
            
            this.uploadZone.addEventListener('dragleave', () => {
                this.uploadZone.classList.remove('drag-over');
            });
            
            this.uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                this.uploadZone.classList.remove('drag-over');
                this.handleFileSelect(e.dataTransfer.files);
            });
        }
        
        // 处理按钮事件
        if (this.processUploadBtn) {
            this.processUploadBtn.addEventListener('click', () => {
                this.processUploadedFiles();
            });
        }
        
        // 清空按钮事件
        if (this.clearUploadBtn) {
            this.clearUploadBtn.addEventListener('click', () => {
                this.clearUploadedFiles();
            });
        }
        

    }
    

    

    

    

    

    

    
    handleFileSelect(files) {
        if (!files || files.length === 0) return;
        
        Array.from(files).forEach(file => {
            this.addFileToList(file);
        });
        
        this.updateProcessButtonState();
    }
    
    addFileToList(file) {
        // 验证文件类型
        const allowedTypes = ['.csv', '.xlsx', '.xls'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExtension)) {
            Toast.error(`不支持的文件类型: ${file.name}`);
            return;
        }
        
        // 验证文件大小 (最大50MB)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            Toast.error(`文件过大: ${file.name} (最大50MB)`);
            return;
        }
        
        const fileData = {
            id: Date.now() + Math.random(),
            file: file,
            name: file.name,
            size: file.size,
            type: file.type,
            status: 'pending',
            progress: 0
        };
        
        this.uploadedFiles.push(fileData);
        this.renderFileItem(fileData);
    }
    
    renderFileItem(fileData) {
        const fileItem = document.createElement('div');
        fileItem.className = 'upload-file-item';
        fileItem.dataset.fileId = fileData.id;
        
        const statusClass = `status-${fileData.status}`;
        const statusIcon = this.getStatusIcon(fileData.status);
        const statusText = this.getStatusText(fileData.status);
        
        fileItem.innerHTML = `
            <div class="upload-file-info">
                <div class="upload-file-name">${fileData.name}</div>
                <div class="upload-file-meta">${this.formatFileSize(fileData.size)}</div>
            </div>
            <div class="upload-file-status">
                <i class="fas ${statusIcon} status-icon ${statusClass}"></i>
                <span class="status-text ${statusClass}">${statusText}</span>
            </div>
        `;
        
        this.uploadFilesList.appendChild(fileItem);
    }
    
    getStatusIcon(status) {
        const icons = {
            pending: 'fa-clock',
            uploading: 'fa-spinner fa-spin',
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle'
        };
        return icons[status] || 'fa-question';
    }
    
    getStatusText(status) {
        const texts = {
            pending: '等待上传',
            uploading: '上传中',
            success: '上传成功',
            error: '上传失败'
        };
        return texts[status] || '未知状态';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    updateProcessButtonState() {
        if (!this.processUploadBtn) return;
        
        const hasFiles = this.uploadedFiles.length > 0;
        const allUploaded = this.uploadedFiles.every(file => file.status === 'success');
        const hasValidToken = this.currentToken.length >= 10;
        
        // 只有在有有效Token且有文件时才启用处理按钮
        this.processUploadBtn.disabled = !hasFiles || !allUploaded || !hasValidToken || this.isUploading;
        
        // 更新按钮文本提示
        if (!hasValidToken) {
            this.processUploadBtn.innerHTML = '<i class="fas fa-key"></i> 需要Token';
            this.processUploadBtn.title = '请先输入有效的Token';
        } else if (!hasFiles) {
            this.processUploadBtn.innerHTML = '<i class="fas fa-cogs"></i> 处理文件';
            this.processUploadBtn.title = '请先上传文件';
        } else if (!allUploaded) {
            this.processUploadBtn.innerHTML = '<i class="fas fa-upload"></i> 等待上传';
            this.processUploadBtn.title = '请等待文件上传完成';
        } else {
            this.processUploadBtn.innerHTML = '<i class="fas fa-cogs"></i> 处理文件';
            this.processUploadBtn.title = '处理已上传的文件';
        }
    }
    
    async processUploadedFiles() {
        if (this.uploadedFiles.length === 0) {
            Toast.warning('请先上传文件');
            return;
        }
        
        const successfulFiles = this.uploadedFiles.filter(file => file.status === 'success');
        if (successfulFiles.length === 0) {
            Toast.warning('没有成功上传的文件');
            return;
        }
        
        this.isUploading = true;
        this.processUploadBtn.disabled = true;
        
        try {
            // 准备处理文件的数据
            const fileNames = successfulFiles.map(file => file.name);
            
            // 调用处理接口
            const response = await fetch('/api/upload/process_files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: fileNames
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                Toast.success('文件处理成功');
                
                // 如果有高德API功能，可以在这里触发
                if (window.gaodeManager && result.data?.suggest_gaode) {
                    // 询问用户是否要进行高德电话查询
                    setTimeout(() => {
                        if (confirm('文件处理完成，是否要进行高德电话查询？')) {
                            this.triggerGaodeQuery(result.data.processed_files);
                        }
                    }, 1000);
                }
            } else {
                Toast.error(result.error || '文件处理失败');
            }
        } catch (error) {
            console.error('处理文件失败:', error);
            Toast.error('处理文件失败: ' + error.message);
        } finally {
            this.isUploading = false;
            this.updateProcessButtonState();
        }
    }
    
    triggerGaodeQuery(files) {
        if (window.gaodeManager) {
            // 将处理后的文件信息传递给高德管理器
            if (files && files.length > 0) {
                window.gaodeManager.setUploadedFiles(files.map(fileName => ({
                    name: fileName,
                    size: 0, // 文件大小在这里不重要
                    source: 'upload'
                })));
            }
            
            // 显示高德区域
            const gaodeSection = document.querySelector('.gaode-section');
            if (gaodeSection) {
                gaodeSection.scrollIntoView({ behavior: 'smooth' });
                gaodeSection.style.borderTop = '3px solid var(--success-color)';
                setTimeout(() => {
                    gaodeSection.style.borderTop = '2px solid var(--warning-color)';
                }, 2000);
            }
        }
    }
    
    clearUploadedFiles() {
        this.uploadedFiles = [];
        if (this.uploadFilesList) {
            this.uploadFilesList.innerHTML = '';
        }
        if (this.fileInput) {
            this.fileInput.value = '';
        }
        this.updateProcessButtonState();
        Toast.info('已清空上传列表');
    }
    
    updateFileProgress(fileId, progress, status = null) {
        const fileItem = document.querySelector(`[data-file-id="${fileId}"]`);
        if (!fileItem) return;
        
        const fileData = this.uploadedFiles.find(f => f.id === fileId);
        if (fileData) {
            fileData.progress = progress;
            if (status) {
                fileData.status = status;
            }
        }
        
        const statusElement = fileItem.querySelector('.upload-file-status');
        if (statusElement) {
            const statusClass = status || fileData.status;
            const statusIcon = this.getStatusIcon(statusClass);
            const statusText = this.getStatusText(statusClass);
            
            statusElement.innerHTML = `
                <i class="fas ${statusIcon} status-icon status-${statusClass}"></i>
                <span class="status-text status-${statusClass}">${statusText}</span>
            `;
        }
        
        this.updateProcessButtonState();
    }
    
    showUploadProgress() {
        if (this.uploadProgress) {
            this.uploadProgress.style.display = 'block';
            this.uploadProgressLabel.textContent = '上传中...';
            this.uploadProgressPercentage.textContent = '0%';
            this.uploadProgressBar.style.width = '0%';
            this.uploadProgressDetails.textContent = '';
        }
    }
    
    updateUploadProgress(progress, filename = '') {
        if (this.uploadProgressPercentage) {
            this.uploadProgressPercentage.textContent = `${Math.round(progress)}%`;
        }
        if (this.uploadProgressBar) {
            this.uploadProgressBar.style.width = `${progress}%`;
        }
        
        if (filename && this.uploadProgressDetails) {
            this.uploadProgressDetails.textContent = `正在上传: ${filename}`;
        }
    }
    
    hideUploadProgress() {
        if (this.uploadProgress) {
            this.uploadProgress.style.display = 'none';
        }
    }
    
    // 真实文件上传过程
    async simulateFileUpload(fileData) {
        if (!this.currentToken || this.currentToken.length < 10) {
            throw new Error('请先输入有效的Token');
        }
        
        this.showUploadProgress();
        this.updateFileProgress(fileData.id, 0, 'uploading');
        
        const formData = new FormData();
        formData.append('file', fileData.file);
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.currentToken}`,
                    'X-API-Token': this.currentToken
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            this.updateFileProgress(fileData.id, 100, 'success');
            this.hideUploadProgress();
            Toast.success(`文件 ${fileData.name} 上传成功`);
            
            return { success: true, fileData, result };
        } catch (error) {
            console.error('Upload error:', error);
            this.updateFileProgress(fileData.id, 0, 'error');
            this.hideUploadProgress();
            Toast.error(`文件 ${fileData.name} 上传失败: ${error.message}`);
            throw error;
        }
    }
    
    // 批量上传文件
    async uploadAllFiles() {
        if (this.currentToken.length < 10) {
            Toast.warning('请先输入有效的Token');
            return;
        }
        
        if (this.uploadedFiles.length === 0) {
            Toast.warning('请先选择文件');
            return;
        }
        
        const pendingFiles = this.uploadedFiles.filter(file => file.status === 'pending');
        if (pendingFiles.length === 0) {
            Toast.info('所有文件已上传');
            return;
        }
        
        for (const fileData of pendingFiles) {
            try {
                await this.simulateFileUpload(fileData);
            } catch (error) {
                console.error('上传文件失败:', error);
                this.updateFileProgress(fileData.id, 0, 'error');
                Toast.error(`文件 ${fileData.name} 上传失败`);
            }
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    window.uploadManager = new UploadManager();
});