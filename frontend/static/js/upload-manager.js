/**
 * 文件上传管理器
 * 处理文件上传、进度显示和文件处理功能
 */

class UploadManager {
    constructor() {
        this.uploadedFiles = [];
        this.isUploading = false;
        this.initElements();
        this.bindEvents();
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
    }

    bindEvents() {
        // 文件选择事件
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // 拖拽事件
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

        // 处理按钮事件
        this.processUploadBtn.addEventListener('click', () => {
            this.processUploadedFiles();
        });

        // 清空按钮事件
        this.clearUploadBtn.addEventListener('click', () => {
            this.clearUploadedFiles();
        });
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
        const hasFiles = this.uploadedFiles.length > 0;
        const allUploaded = this.uploadedFiles.every(file => file.status === 'success');
        this.processUploadBtn.disabled = !hasFiles || !allUploaded || this.isUploading;
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
            const response = await ApiClient.post('/api/upload/process_files', {
                files: fileNames
            });

            if (response.success) {
                Toast.success('文件处理成功');
                
                // 如果有高德API功能，可以在这里触发
                if (window.gaodeManager && response.data?.suggest_gaode) {
                    // 询问用户是否要进行高德电话查询
                    if (confirm('文件处理完成，是否要进行高德电话查询？')) {
                        this.triggerGaodeQuery(response.data.processed_files);
                    }
                }
            } else {
                Toast.error(response.error || '文件处理失败');
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
            files.forEach(fileName => {
                // 这里可以根据需要设置高德管理器的文件
                console.log('触发高德查询:', fileName);
            });
            
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
        this.uploadFilesList.innerHTML = '';
        this.fileInput.value = '';
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
        this.uploadProgress.style.display = 'block';
        this.uploadProgressLabel.textContent = '上传中...';
        this.uploadProgressPercentage.textContent = '0%';
        this.uploadProgressBar.style.width = '0%';
        this.uploadProgressDetails.textContent = '';
    }

    updateUploadProgress(progress, filename = '') {
        this.uploadProgressPercentage.textContent = `${Math.round(progress)}%`;
        this.uploadProgressBar.style.width = `${progress}%`;
        
        if (filename) {
            this.uploadProgressDetails.textContent = `正在上传: ${filename}`;
        }
    }

    hideUploadProgress() {
        this.uploadProgress.style.display = 'none';
    }

    // 模拟文件上传过程（实际项目中需要替换为真实的上传逻辑）
    async simulateFileUpload(fileData) {
        this.showUploadProgress();
        this.updateFileProgress(fileData.id, 0, 'uploading');

        return new Promise((resolve) => {
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 20;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                    
                    this.updateFileProgress(fileData.id, 100, 'success');
                    this.hideUploadProgress();
                    Toast.success(`文件 ${fileData.name} 上传成功`);
                    
                    resolve({ success: true, fileData });
                } else {
                    this.updateFileProgress(fileData.id, progress);
                    this.updateUploadProgress(progress, fileData.name);
                }
            }, 200);
        });
    }

    // 批量上传文件
    async uploadAllFiles() {
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