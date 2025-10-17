/**
 * 任务监控模块 - 实时监控爬取任务状态
 */

class TaskMonitor {
    constructor() {
        this.currentTaskId = null;
        this.monitorInterval = null;
        this.statusUpdateCallbacks = [];
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // 绑定停止任务按钮
        const stopBtn = document.getElementById('stopCrawlBtn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.stopTask();
            });
        }

        // 绑定日志面板事件
        const logToggleBtn = document.getElementById('toggleLogBtn');
        if (logToggleBtn) {
            logToggleBtn.addEventListener('click', () => {
                this.toggleLogPanel();
            });
        }

        const logCloseBtn = document.getElementById('logPanelClose');
        if (logCloseBtn) {
            logCloseBtn.addEventListener('click', () => {
                this.hideLogPanel();
            });
        }

        const logClearBtn = document.getElementById('logPanelClear');
        if (logClearBtn) {
            logClearBtn.addEventListener('click', () => {
                this.clearLogMessages();
            });
        }

        const logDownloadBtn = document.getElementById('logPanelDownload');
        if (logDownloadBtn) {
            logDownloadBtn.addEventListener('click', () => {
                this.downloadLog();
            });
        }

        // 点击遮罩关闭日志面板
        const logPanel = document.getElementById('crawlLogPanel');
        if (logPanel) {
            logPanel.addEventListener('click', (e) => {
                if (e.target === logPanel) {
                    this.hideLogPanel();
                }
            });
        }
    }

    startMonitoring(taskId) {
        this.currentTaskId = taskId;
        this.showProgress();
        
        // 开始定期检查任务状态 - 减少频率，增加详细日志显示
        this.monitorInterval = setInterval(() => {
            this.checkTaskStatus();
        }, 5000); // 每5秒检查一次，减少服务器压力

        // 立即检查一次
        this.checkTaskStatus();
        
        // 显示详细日志区域
        this.showLogPanel();
    }

    stopMonitoring() {
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
        }
        this.currentTaskId = null;
        this.hideProgress();
    }

    async checkTaskStatus() {
        if (!this.currentTaskId) return;

        try {
            const response = await ApiClient.get(`/api/crawler/status/${this.currentTaskId}`);
            
            if (response.success) {
                this.updateTaskStatus(response.data);
                
                // 如果任务完成或失败，停止监控
                if (response.data.status === 'completed' || response.data.status === 'failed') {
                    this.stopMonitoring();
                    this.onTaskFinished(response.data);
                }
            }
        } catch (error) {
            console.error('检查任务状态失败:', error);
            // 如果连续出错，可能是网络问题，暂时不停止监控
        }
    }

    updateTaskStatus(taskData) {
        // 更新进度条
        this.updateProgress(taskData);
        
        // 添加详细日志到控制台
        if (taskData.message) {
            console.log(`[${taskData.type?.toUpperCase() || 'INFO'}] ${taskData.message}`);
        }
        
        // 显示详细日志到界面
        this.addLogMessage(taskData);
        
        // 触发状态更新回调
        this.statusUpdateCallbacks.forEach(callback => {
            try {
                callback(taskData);
            } catch (error) {
                console.error('状态更新回调失败:', error);
            }
        });
    }

    updateProgress(taskData) {
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressLabel = document.getElementById('progressLabel');
        const progressPercentage = document.getElementById('progressPercentage');
        const progressDetails = document.getElementById('progressDetails');

        if (!progressContainer) return;

        // 显示进度容器
        progressContainer.style.display = 'block';

        // 更新进度条
        const progress = taskData.progress || 0;
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(progress)}%`;
        }

        // 更新状态文本
        if (progressLabel) {
            const statusText = this.getStatusText(taskData.status);
            progressLabel.textContent = taskData.message || statusText;
        }

        // 更新详细信息
        if (progressDetails && taskData.extra_info) {
            const details = [];
            
            if (taskData.extra_info.stats) {
                const stats = taskData.extra_info.stats;
                if (stats.captcha_count > 0) {
                    details.push(`
                        <span class="progress-stat">
                            <i class="fas fa-shield-alt text-warning"></i>
                            验证码: ${stats.captcha_count}次
                        </span>
                    `);
                }
                if (stats.skipped_pages > 0) {
                    details.push(`
                        <span class="progress-stat">
                            <i class="fas fa-skip-forward text-info"></i>
                            跳过: ${stats.skipped_pages}页
                        </span>
                    `);
                }
                if (stats.page_refresh_count > 0) {
                    details.push(`
                        <span class="progress-stat">
                            <i class="fas fa-redo text-primary"></i>
                            刷新: ${stats.page_refresh_count}次
                        </span>
                    `);
                }
            }

            if (taskData.is_running) {
                details.push(`
                    <span class="progress-stat">
                        <i class="fas fa-clock text-muted"></i>
                        ${DateUtils.formatRelative(taskData.start_time)}开始
                    </span>
                `);
            }

            progressDetails.innerHTML = details.join('');
        }
    }

    getStatusText(status) {
        const statusTexts = {
            pending: '等待开始...',
            queued: '排队中...',
            running: '正在爬取...',
            completed: '爬取完成',
            failed: '爬取失败',
            cancelled: '已取消'
        };
        return statusTexts[status] || '未知状态';
    }

    showProgress() {
        const progressContainer = document.getElementById('progressContainer');
        const startBtn = document.getElementById('startCrawlBtn');
        const stopBtn = document.getElementById('stopCrawlBtn');

        if (progressContainer) {
            progressContainer.style.display = 'block';
        }

        if (startBtn) {
            startBtn.style.display = 'none';
        }

        if (stopBtn) {
            stopBtn.style.display = 'inline-flex';
        }

        // 重置进度
        this.updateProgress({
            progress: 0,
            status: 'pending',
            message: '准备开始...'
        });
    }

    hideProgress() {
        const progressContainer = document.getElementById('progressContainer');
        const startBtn = document.getElementById('startCrawlBtn');
        const stopBtn = document.getElementById('stopCrawlBtn');

        if (progressContainer) {
            progressContainer.style.display = 'none';
        }

        if (startBtn) {
            startBtn.style.display = 'inline-flex';
        }

        if (stopBtn) {
            stopBtn.style.display = 'none';
        }
        
        // 隐藏日志面板
        this.hideLogPanel();
    }

    showLogPanel() {
        const logPanel = document.getElementById('crawlLogPanel');
        if (logPanel) {
            logPanel.style.display = 'block';
            // 不自动清空日志，保留历史日志
            // this.clearLogMessages();
        }
    }

    hideLogPanel() {
        const logPanel = document.getElementById('crawlLogPanel');
        if (logPanel) {
            logPanel.style.display = 'none';
        }
    }

    toggleLogPanel() {
        const logPanel = document.getElementById('crawlLogPanel');
        if (logPanel) {
            if (logPanel.style.display === 'none' || logPanel.style.display === '') {
                this.showLogPanel();
            } else {
                this.hideLogPanel();
            }
        }
    }

    addLogMessage(taskData) {
        // 添加到控制台
        console.log(`[${taskData.type?.toUpperCase() || 'INFO'}] ${taskData.message}`);
        
        // 添加到日志面板
        const logContainer = document.getElementById('crawlLogContainer');
        if (!logContainer) return;

        const message = taskData.message || '';
        if (!message.trim()) return;

        const timestamp = new Date().toLocaleTimeString('zh-CN');
        const type = taskData.type || 'info';
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `
            <div class="log-timestamp">${timestamp}</div>
            <div class="log-content">
                <span class="log-type ${type}">${type.toUpperCase()}</span>
                <span class="log-message">${this.escapeHtml(message)}</span>
            </div>
        `;

        logContainer.appendChild(logEntry);
        
        // 自动滚动到底部
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // 限制日志条目数量
        const maxEntries = 500;
        while (logContainer.children.length > maxEntries) {
            logContainer.removeChild(logContainer.firstChild);
        }
    }

    clearLogMessages() {
        const logContainer = document.getElementById('crawlLogContainer');
        if (logContainer) {
            logContainer.innerHTML = '<div class="text-muted text-center p-3">日志已清空</div>';
            // 3秒后清除提示信息
            setTimeout(() => {
                if (logContainer.innerHTML.includes('日志已清空')) {
                    logContainer.innerHTML = '';
                }
            }, 3000);
        }
    }

    downloadLog() {
        const logContainer = document.getElementById('crawlLogContainer');
        if (!logContainer) return;

        const logs = [];
        const entries = logContainer.querySelectorAll('.log-entry');
        
        entries.forEach(entry => {
            const timestamp = entry.querySelector('.log-timestamp')?.textContent || '';
            const type = entry.querySelector('.log-type')?.textContent || '';
            const message = entry.querySelector('.log-message')?.textContent || '';
            logs.push(`[${timestamp}] [${type}] ${message}`);
        });

        const blob = new Blob([logs.join('\n')], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `crawl-log-${this.currentTaskId || Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async stopTask() {
        if (!this.currentTaskId) return;

        if (!confirm('确定要停止当前爬取任务吗？')) {
            return;
        }

        Loading.show('停止任务中...');

        try {
            const response = await ApiClient.post(`/api/crawler/cancel/${this.currentTaskId}`);
            
            if (response.success) {
                Toast.success(response.message);
                this.stopMonitoring();
            } else {
                Toast.error(response.error || '停止任务失败');
            }
        } catch (error) {
            console.error('停止任务失败:', error);
            Toast.error('停止任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    onTaskFinished(taskData) {
        const isSuccess = taskData.status === 'completed';
        
        if (isSuccess) {
            Toast.success(`爬取完成！共获取 ${taskData.total_shops || 0} 个商铺数据`);
            
            // 刷新历史记录和文件列表
            if (window.app) {
                window.app.loadHistory();
                window.app.loadFiles();
                window.app.loadStats();
            }
        } else {
            Toast.error('爬取任务失败，请查看详细信息');
        }

        // 显示任务详情
        this.showTaskDetail(taskData);

        // 重新启用表单
        if (window.app) {
            window.app.updateFormState();
        }
    }

    showTaskDetail(taskData) {
        const modal = document.getElementById('taskDetailModal');
        const content = document.getElementById('taskDetailContent');
        
        if (!modal || !content) return;

        const isSuccess = taskData.status === 'completed';
        const statusClass = isSuccess ? 'text-success' : 'text-danger';
        const statusIcon = isSuccess ? 'fa-check-circle' : 'fa-exclamation-circle';

        content.innerHTML = `
            <div class="task-detail-header mb-3">
                <h4>
                    <i class="fas ${statusIcon} ${statusClass}"></i>
                    任务${isSuccess ? '完成' : '失败'}
                </h4>
            </div>
            
            <div class="task-detail-info">
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>任务ID:</strong></div>
                    <div class="col-sm-9"><code>${taskData.task_id}</code></div>
                </div>
                
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>开始时间:</strong></div>
                    <div class="col-sm-9">${DateUtils.formatDate(taskData.start_time)}</div>
                </div>
                
                ${taskData.end_time ? `
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>结束时间:</strong></div>
                    <div class="col-sm-9">${DateUtils.formatDate(taskData.end_time)}</div>
                </div>
                ` : ''}
                
                ${taskData.total_shops ? `
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>商铺数量:</strong></div>
                    <div class="col-sm-9">${NumberUtils.format(taskData.total_shops)} 个</div>
                </div>
                ` : ''}
                
                ${taskData.error_message ? `
                <div class="row mb-3">
                    <div class="col-sm-3"><strong>错误信息:</strong></div>
                    <div class="col-sm-9 text-danger">${taskData.error_message}</div>
                </div>
                ` : ''}
            </div>
            
            <div class="task-actions mt-4">
                <button class="btn btn-secondary" onclick="Modal.hide('taskDetailModal')">
                    <i class="fas fa-times"></i> 关闭
                </button>
                ${taskData.output_file ? `
                <a href="/downloads/${taskData.output_file}" class="btn btn-primary" download>
                    <i class="fas fa-download"></i> 下载结果
                </a>
                ` : ''}
            </div>
        `;

        Modal.show('taskDetailModal');
    }

    addStatusCallback(callback) {
        if (typeof callback === 'function') {
            this.statusUpdateCallbacks.push(callback);
        }
    }

    removeStatusCallback(callback) {
        const index = this.statusUpdateCallbacks.indexOf(callback);
        if (index > -1) {
            this.statusUpdateCallbacks.splice(index, 1);
        }
    }

    isMonitoring() {
        return !!this.monitorInterval;
    }

    getCurrentTaskId() {
        return this.currentTaskId;
    }
}

// 创建全局任务监控器实例
window.taskMonitor = new TaskMonitor();