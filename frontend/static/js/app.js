/**
 * 主应用逻辑
 */

class CrawlerApp {
    constructor() {
        this.selectedCategories = new Set();
        this.crawledCombinations = new Set();
        this.cities = [];
        this.categories = [];
        this.appConfig = {};
        this.init();
    }

    async init() {
        try {
            // 初始化工具组件
            Modal.init();
            
            // 绑定事件
            this.bindEvents();
            
            // 加载初始数据
            await this.loadInitialData();
            
            // 检查API状态
            this.checkApiStatus();
            
            // 定期刷新数据
            this.startPeriodicRefresh();
            
            // 确保初始表单状态正确
            setTimeout(() => {
                this.updateFormState();
                console.log('应用初始化完成，表单状态已更新');
            }, 1000);
            
            console.log('应用初始化完成');
        } catch (error) {
            console.error('应用初始化失败:', error);
            Toast.error('应用初始化失败，请刷新页面重试');
        }
    }

    bindEvents() {
        // 城市选择
        const citySelect = document.getElementById('citySelect');
        if (citySelect) {
            citySelect.addEventListener('change', () => {
                this.onCityChange();
            });
        }

        // 页数范围选择
        const pageRangeRadios = document.querySelectorAll('input[name="pageRange"]');
        pageRangeRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                this.onPageRangeChange();
            });
        });

        // 自定义页数范围输入
        const startPage = document.getElementById('startPage');
        const endPage = document.getElementById('endPage');
        if (startPage && endPage) {
            [startPage, endPage].forEach(input => {
                input.addEventListener('input', () => {
                    this.updateRangeInfo();
                    this.updateFormState();
                });
            });
        }

        // 开始爬取按钮
        const startBtn = document.getElementById('startCrawlBtn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.startCrawling();
            });
        }

        // 检查限制按钮
        const checkBtn = document.getElementById('checkRestrictionsBtn');
        if (checkBtn) {
            checkBtn.addEventListener('click', () => {
                this.checkRestrictions();
            });
        }

        // 重要提醒按钮
        const noticesBtn = document.getElementById('showNoticesBtn');
        if (noticesBtn) {
            noticesBtn.addEventListener('click', () => {
                this.showImportantNotices();
            });
        }

        // Cookie帮助按钮
        const cookieHelpBtn = document.getElementById('cookieHelpBtn');
        if (cookieHelpBtn) {
            cookieHelpBtn.addEventListener('click', () => {
                Modal.show('cookieHelpModal');
            });
        }

        // 加载更多历史记录
        const loadMoreBtn = document.getElementById('loadMoreHistoryBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreHistory();
            });
        }

        // UAT上传按钮
        const uploadBtn = document.getElementById('uploadToUatBtn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                this.showUatUploadInfo();
            });
        }
    }

    async loadInitialData() {
        Loading.show('加载配置信息...');
        
        try {
            // 并行加载所有配置数据
            const [citiesRes, categoriesRes, limitsRes, noticesRes] = await Promise.all([
                ApiClient.get('/api/config/cities'),
                ApiClient.get('/api/config/categories'),
                ApiClient.get('/api/config/limits'),
                ApiClient.get('/api/config/notices')
            ]);

            if (citiesRes.success) {
                this.cities = citiesRes.data;
                this.renderCities();
            }

            if (categoriesRes.success) {
                this.categories = categoriesRes.data;
                this.renderCategories();
            }

            if (limitsRes.success) {
                this.appConfig = limitsRes.data;
            }

            if (noticesRes.success) {
                this.importantNotices = noticesRes.data;
                this.checkShowNotices();
            }

            // 加载其他数据
            await Promise.all([
                this.loadStats(),
                this.loadHistory(),
                this.loadFiles(),
                this.loadQueueStatus()
            ]);

        } catch (error) {
            console.error('加载初始数据失败:', error);
            Toast.error('加载配置失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    renderCities() {
        const citySelect = document.getElementById('citySelect');
        if (!citySelect) return;

        DOMUtils.empty(citySelect);
        
        // 添加默认选项
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '请选择城市...';
        citySelect.appendChild(defaultOption);

        // 添加城市选项
        this.cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.name;
            option.textContent = city.name;
            citySelect.appendChild(option);
        });
    }

    renderCategories() {
        const grid = document.getElementById('categoriesGrid');
        if (!grid) return;

        DOMUtils.empty(grid);

        this.categories.forEach(category => {
            const categoryItem = DOMUtils.createElement('div', 'category-item');
            categoryItem.dataset.category = category.name;

            categoryItem.innerHTML = `
                <input type="checkbox" id="cat_${category.id}" value="${category.name}">
                <label for="cat_${category.id}">${category.name}</label>
            `;

            // 添加点击事件
            categoryItem.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = categoryItem.querySelector('input[type="checkbox"]');
                    checkbox.click();
                }
            });

            // 添加复选框变化事件
            const checkbox = categoryItem.querySelector('input[type="checkbox"]');
            checkbox.addEventListener('change', () => {
                this.onCategoryChange(category.name, checkbox.checked);
            });

            grid.appendChild(categoryItem);
        });
    }

    onCityChange() {
        const citySelect = document.getElementById('citySelect');
        const selectedCity = citySelect.value;

        if (selectedCity) {
            this.loadCrawledCombinations(selectedCity);
        }

        this.updateFormState();
    }

    async loadCrawledCombinations(city) {
        // 移除已爬取组合检查，不再禁用品类选择
        this.crawledCombinations.clear();
        this.updateCategoryDisplay();
    }

    updateCategoryDisplay() {
        const grid = document.getElementById('categoriesGrid');
        if (!grid) return;

        grid.querySelectorAll('.category-item').forEach(item => {
            const categoryName = item.dataset.category;
            const checkbox = item.querySelector('input[type="checkbox"]');
            
            // 重置状态
            item.classList.remove('crawled', 'disabled');
            checkbox.disabled = false;

            // 移除已爬取标记和禁用逻辑
            // 不再根据已爬取组合禁用品类选择
        });

        this.updateSelectedCategories();
        this.updateFormState();
    }

    onCategoryChange(categoryName, isSelected) {
        if (isSelected) {
            if (this.selectedCategories.size >= 2) {
                Toast.warning('最多只能选择2个品类');
                // 取消选择
                const item = document.querySelector(`[data-category="${categoryName}"] input`);
                if (item) item.checked = false;
                return;
            }
            this.selectedCategories.add(categoryName);
        } else {
            this.selectedCategories.delete(categoryName);
        }

        this.updateSelectedCategories();
        this.updateFormState();
    }

    updateSelectedCategories() {
        const container = document.getElementById('selectedCategories');
        if (!container) return;

        DOMUtils.empty(container);

        this.selectedCategories.forEach(categoryName => {
            const tag = DOMUtils.createElement('div', 'selected-category');
            tag.innerHTML = `
                <span>${categoryName}</span>
                <button class="remove-btn" onclick="app.removeCategory('${categoryName}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            container.appendChild(tag);
        });

        // 更新品类项的选中状态
        document.querySelectorAll('.category-item').forEach(item => {
            const categoryName = item.dataset.category;
            const checkbox = item.querySelector('input[type="checkbox"]');
            
            if (this.selectedCategories.has(categoryName)) {
                item.classList.add('selected');
                checkbox.checked = true;
            } else {
                item.classList.remove('selected');
                checkbox.checked = false;
            }
        });
    }

    removeCategory(categoryName) {
        this.selectedCategories.delete(categoryName);
        this.updateSelectedCategories();
        this.updateFormState();
    }

    onPageRangeChange() {
        const selectedRange = document.querySelector('input[name="pageRange"]:checked').value;
        const customRangeGroup = document.getElementById('customRangeGroup');
        
        if (selectedRange === 'custom') {
            customRangeGroup.style.display = 'block';
            this.updateRangeInfo();
        } else {
            customRangeGroup.style.display = 'none';
        }
        
        console.log('页数范围改变:', selectedRange);
        this.updateFormState();
    }

    updateRangeInfo() {
        const startPage = document.getElementById('startPage');
        const endPage = document.getElementById('endPage');
        const rangeInfo = document.getElementById('rangeInfo');
        const rangeSummary = rangeInfo.querySelector('.range-summary');
        
        if (!startPage || !endPage || !rangeSummary) return;
        
        const start = parseInt(startPage.value) || 1;
        const end = parseInt(endPage.value) || 1;
        
        // 计算页数范围（允许结束页小于起始页）
        const totalPages = Math.abs(end - start) + 1;
        const minPage = Math.min(start, end);
        const maxPage = Math.max(start, end);
        
        rangeSummary.textContent = `将爬取第${minPage}-${maxPage}页，共${totalPages}页`;
    }

    getPageRangeParams() {
        const selectedRange = document.querySelector('input[name="pageRange"]:checked').value;
        
        switch (selectedRange) {
            case 'first':
                return { start_page: 1, end_page: 15, range_type: 'first' };
            case 'last':
                return { range_type: 'last', page_count: 15 };
            case 'custom':
                const startPageInput = document.getElementById('startPage');
                const endPageInput = document.getElementById('endPage');
                const startPage = parseInt(startPageInput?.value) || 1;
                const endPage = parseInt(endPageInput?.value) || 1;
                
                // 验证数字有效性
                if (isNaN(startPage) || isNaN(endPage) || startPage < 1 || endPage < 1) {
                    console.error('页数范围参数无效:', { startPage, endPage });
                    return { start_page: 1, end_page: 2, range_type: 'custom' };
                }
                
                // 确保返回的范围是正确排序的（小的在前，大的在后）
                const minPage = Math.min(startPage, endPage);
                const maxPage = Math.max(startPage, endPage);
                
                return { start_page: minPage, end_page: maxPage, range_type: 'custom' };
            default:
                return { start_page: 1, end_page: 15, range_type: 'first' };
        }
    }

    updateFormState() {
        const startBtn = document.getElementById('startCrawlBtn');
        const checkBtn = document.getElementById('checkRestrictionsBtn');
        
        if (!startBtn) return;

        const canStart = this.canStartCrawling();
        startBtn.disabled = !canStart;
        
        if (checkBtn) {
            checkBtn.disabled = !cookieManager.isValidCookie();
        }
    }

    canStartCrawling() {
        const citySelect = document.getElementById('citySelect');
        
        const hasCity = citySelect && citySelect.value;
        const hasCategories = this.selectedCategories.size > 0;
        const hasValidRange = this.isValidPageRange();
        const hasCookie = cookieManager.isValidCookie();
        const notMonitoring = !taskMonitor.isMonitoring();

        // 调试信息
        console.log('canStartCrawling检查:', {
            hasCity: hasCity,
            hasCategories: hasCategories,
            hasValidRange: hasValidRange,
            hasCookie: hasCookie,
            notMonitoring: notMonitoring,
            cityValue: citySelect ? citySelect.value : 'null',
            categoriesCount: this.selectedCategories.size,
            currentCookie: cookieManager.getCurrentCookie() ? '有Cookie' : '无Cookie'
        });

        return hasCity && hasCategories && hasValidRange && hasCookie && notMonitoring;
    }

    isValidPageRange() {
        const selectedRange = document.querySelector('input[name="pageRange"]:checked')?.value;
        
        if (selectedRange === 'custom') {
            const startPage = parseInt(document.getElementById('startPage').value);
            const endPage = parseInt(document.getElementById('endPage').value);
            // 允许结束页小于起始页，只要都是有效的正整数且不超过100
            return startPage >= 1 && endPage >= 1 && startPage <= 100 && endPage <= 100;
        }
        
        return true; // 'first' 和 'last' 总是有效的
    }

    async checkRestrictions() {
        const citySelect = document.getElementById('citySelect');
        const city = citySelect.value;
        const categories = Array.from(this.selectedCategories);

        if (!city || categories.length === 0) {
            Toast.warning('请先选择城市和品类');
            return;
        }

        if (!cookieManager.isValidCookie()) {
            Toast.warning('请先验证Cookie');
            return;
        }

        Loading.show('检查爬取限制...');

        try {
            const restrictions = await cookieManager.checkCookieRestrictions(city, categories);
            this.showRestrictions(restrictions);
        } catch (error) {
            console.error('检查限制失败:', error);
            Toast.error('检查限制失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    showRestrictions(restrictions) {
        const container = document.getElementById('restrictionsCheck');
        if (!container) return;

        let html = '';
        let containerClass = 'restrictions-check show';

        if (restrictions.can_use) {
            containerClass += ' success';
            html = `
                <div class="restriction-item">
                    <i class="fas fa-check-circle text-success"></i>
                    <span>所有限制检查通过，可以开始爬取</span>
                </div>
            `;
        } else {
            containerClass += ' error';
            html = '<div class="restriction-item"><i class="fas fa-exclamation-circle"></i><span>发现以下限制问题:</span></div>';
            
            const errors = [];
            
            if (restrictions.restrictions.daily_limit_reached) {
                errors.push(`今日使用次数已达上限 (${restrictions.daily_usage}/${restrictions.max_daily_usage})`);
            }
            
            if (restrictions.restrictions.time_interval_insufficient) {
                errors.push(`距离上次爬取时间不足${restrictions.min_interval_hours}小时`);
            }
            
            if (restrictions.restrictions.combinations_already_crawled) {
                errors.push(`以下组合今日已爬取: ${restrictions.crawled_combinations.join(', ')}`);
            }

            errors.forEach(error => {
                html += `
                    <div class="restriction-item">
                        <i class="fas fa-times text-danger"></i>
                        <span>${error}</span>
                    </div>
                `;
            });
        }

        container.className = containerClass;
        container.innerHTML = html;

        // 自动隐藏
        setTimeout(() => {
            container.classList.remove('show');
        }, 10000);
    }

    async startCrawling() {
        if (!this.canStartCrawling()) {
            Toast.warning('请检查所有必要参数是否正确填写');
            return;
        }

        // 先检查限制
        await this.checkRestrictions();
        
        // 等待一下让用户看到限制检查结果
        await new Promise(resolve => setTimeout(resolve, 1000));

        const citySelect = document.getElementById('citySelect');
        const pageRangeParams = this.getPageRangeParams();

        // 获取城市代码
        const selectedCity = this.cities.find(city => city.name === citySelect.value);
        if (!selectedCity) {
            Toast.error('无效的城市选择');
            return;
        }

        // 获取品类代码
        const selectedCategoryIds = [];
        for (const categoryName of this.selectedCategories) {
            const category = this.categories.find(cat => cat.name === categoryName);
            if (category) {
                selectedCategoryIds.push(category.id);
            }
        }

        if (selectedCategoryIds.length === 0) {
            Toast.error('无效的品类选择');
            return;
        }

        // 获取排序方式
        const sortTypeRadios = document.querySelectorAll('input[name="sortType"]');
        let sortType = 'popularity'; // 默认人气排序
        for (const radio of sortTypeRadios) {
            if (radio.checked) {
                sortType = radio.value;
                break;
            }
        }

        const formData = {
            city: selectedCity.code,  // 发送城市代码，如 'xian'
            categories: selectedCategoryIds,  // 发送品类ID，如 ['g34351']
            cookie_string: cookieManager.getCurrentCookie(),
            sort_type: sortType,  // 添加排序参数
            ...pageRangeParams
        };

        // 表单验证
        const validation = Validator.validateForm(formData);
        if (!validation.valid) {
            Toast.error('表单验证失败: ' + validation.errors.join(', '));
            return;
        }

        Loading.show('创建爬取任务...');

        try {
            const response = await ApiClient.post('/api/crawler/start', formData);
            
            if (response.success) {
                Toast.success('爬取任务已创建');
                
                // 开始监控任务
                taskMonitor.startMonitoring(response.data.task_id);
                
                // 更新表单状态
                this.updateFormState();
                
                // 显示估算时间
                if (response.data.estimated_time) {
                    Toast.info(`预计耗时: ${response.data.estimated_time} 分钟`);
                }
            } else {
                Toast.error(response.error || '创建任务失败');
                
                // 如果有限制信息，显示出来
                if (response.restrictions) {
                    this.showRestrictions(response.restrictions);
                }
            }
        } catch (error) {
            console.error('开始爬取失败:', error);
            Toast.error('开始爬取失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    async loadStats() {
        try {
            const response = await ApiClient.get('/api/stats/dashboard');
            
            if (response.success) {
                this.updateStats(response.data);
            }
        } catch (error) {
            console.error('加载统计信息失败:', error);
        }
    }

    updateStats(data) {
        const stats = data.crawl_stats || {};
        const cookieStats = data.cookie_stats || {};
        const queueStats = data.queue_stats || {};

        // 更新统计数字
        this.updateStatValue('totalTasks', stats.total_tasks);
        this.updateStatValue('todayTasks', stats.today_tasks);
        this.updateStatValue('totalShops', stats.total_shops);
        this.updateStatValue('successRate', NumberUtils.formatPercentage(stats.completed_tasks, stats.total_tasks));

        // 更新队列状态
        this.updateStatValue('pendingTasks', queueStats.pending_tasks);
        this.updateStatValue('runningTasks', queueStats.running_tasks);
    }

    updateStatValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value !== undefined ? value : '-';
        }
    }

    async loadHistory(page = 1) {
        try {
            const response = await ApiClient.get('/api/crawler/history', {
                page: page,
                per_page: 10
            });
            
            if (response.success) {
                this.renderHistory(response.data.records, page === 1);
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
        }
    }

    renderHistory(records, clear = true) {
        const container = document.getElementById('historyList');
        if (!container) return;

        if (clear) {
            DOMUtils.empty(container);
        }

        if (records.length === 0) {
            container.innerHTML = '<div class="text-muted text-center">暂无历史记录</div>';
            return;
        }

        records.forEach(record => {
            const item = this.createHistoryItem(record);
            container.appendChild(item);
        });
    }

    createHistoryItem(record) {
        const item = DOMUtils.createElement('div', 'history-item');
        
        const statusClass = {
            completed: 'completed',
            failed: 'failed',
            running: 'running',
            pending: 'running'
        }[record.status] || 'failed';

        const categories = Array.isArray(record.categories) ? 
            record.categories.join(', ') : record.categories;

        // 检查是否有输出文件可下载
        const hasOutputFile = record.output_file && record.status === 'completed';

        item.innerHTML = `
            <div class="history-header">
                <div class="history-title">${record.city} - ${categories}</div>
                <div class="history-actions">
                    ${hasOutputFile ? `
                        <button class="btn btn-sm btn-outline-primary download-btn" 
                                data-filename="${record.output_file}" 
                                title="下载结果文件">
                            <i class="fas fa-download"></i>
                        </button>
                    ` : ''}
                    <div class="history-status ${statusClass}">${this.getStatusText(record.status)}</div>
                </div>
            </div>
            <div class="history-details">
                <div class="history-detail">
                    <i class="fas fa-calendar"></i>
                    ${DateUtils.formatRelative(record.created_at)}
                </div>
                ${record.total_shops ? `
                <div class="history-detail">
                    <i class="fas fa-store"></i>
                    ${NumberUtils.format(record.total_shops)} 个商铺
                </div>
                ` : ''}
                ${record.captcha_count ? `
                <div class="history-detail">
                    <i class="fas fa-shield-alt text-warning"></i>
                    ${record.captcha_count} 次验证码
                </div>
                ` : ''}
                ${hasOutputFile ? `
                <div class="history-detail">
                    <i class="fas fa-file-csv text-success"></i>
                    ${record.output_file}
                </div>
                ` : ''}
            </div>
        `;

        // 下载按钮事件
        const downloadBtn = item.querySelector('.download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止冒泡到历史记录项的点击事件
                const filename = downloadBtn.getAttribute('data-filename');
                this.downloadFile(filename);
            });
        }

        // 点击历史记录项显示详情（排除下载按钮区域）
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.download-btn')) {
                this.showHistoryDetail(record);
            }
        });

        return item;
    }

    getStatusText(status) {
        const statusTexts = {
            pending: '等待中',
            running: '进行中',
            completed: '已完成',
            failed: '已失败',
            cancelled: '已取消'
        };
        return statusTexts[status] || status;
    }

    showHistoryDetail(record) {
        // 显示历史记录详情
        taskMonitor.showTaskDetail(record);
    }

    downloadFile(filename) {
        if (!filename) {
            Toast.error('文件名无效');
            return;
        }

        // 创建下载链接
        const downloadUrl = `/api/upload/download/${encodeURIComponent(filename)}`;
        
        // 使用fetch下载文件
        fetch(downloadUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`下载失败: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // 创建下载链接
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                Toast.success('文件下载成功');
            })
            .catch(error => {
                console.error('下载文件失败:', error);
                Toast.error(`下载失败: ${error.message}`);
            });
    }

    async loadFiles() {
        try {
            const response = await ApiClient.get('/api/upload/files');
            
            if (response.success) {
                this.renderFiles(response.data);
            }
        } catch (error) {
            console.error('加载文件列表失败:', error);
        }
    }

    renderFiles(files) {
        const container = document.getElementById('filesList');
        if (!container) return;

        DOMUtils.empty(container);

        if (files.length === 0) {
            container.innerHTML = '<div class="text-muted text-center">暂无文件</div>';
            return;
        }

        files.slice(0, 5).forEach(file => { // 只显示最新的5个文件
            const item = this.createFileItem(file);
            container.appendChild(item);
        });
    }

    createFileItem(file) {
        const item = DOMUtils.createElement('div', 'file-item');
        
        item.innerHTML = `
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-meta">
                    ${FileUtils.formatSize(file.size)} • 
                    ${DateUtils.formatRelative(file.created_at)}
                </div>
            </div>
            <div class="file-actions">
                <button class="file-action-btn" onclick="app.downloadFile('${file.filename}')" title="下载">
                    <i class="fas fa-download"></i>
                </button>
                <button class="file-action-btn" onclick="app.previewFile('${file.filename}')" title="预览">
                    <i class="fas fa-eye"></i>
                </button>
            </div>
        `;

        return item;
    }

    downloadFile(filename) {
        const url = `/api/upload/download/${filename}`;
        FileUtils.downloadFile(url, filename);
    }

    async previewFile(filename) {
        try {
            const response = await ApiClient.get(`/api/upload/preview/${filename}`);
            
            if (response.success) {
                this.showFilePreview(response.data);
            } else {
                Toast.error('预览失败: ' + response.error);
            }
        } catch (error) {
            console.error('预览文件失败:', error);
            Toast.error('预览文件失败: ' + error.message);
        }
    }

    showFilePreview(data) {
        // 这里可以实现文件预览功能
        Toast.info('文件预览功能开发中...');
    }

    async loadQueueStatus() {
        try {
            const response = await ApiClient.get('/api/crawler/queue-status');
            
            if (response.success) {
                this.updateQueueStatus(response.data);
            }
        } catch (error) {
            console.error('加载队列状态失败:', error);
        }
    }

    updateQueueStatus(data) {
        this.updateStatValue('pendingTasks', data.pending_tasks || 0);
        this.updateStatValue('runningTasks', data.running_tasks || 0);
    }

    async checkApiStatus() {
        try {
            const response = await ApiClient.get('/api/status');
            
            const statusDot = document.getElementById('apiStatus');
            const statusText = document.getElementById('apiStatusText');
            
            if (response.status === 'running') {
                statusDot.className = 'status-dot online';
                statusText.textContent = '服务正常';
            } else {
                statusDot.className = 'status-dot offline';
                statusText.textContent = '服务异常';
            }
        } catch (error) {
            const statusDot = document.getElementById('apiStatus');
            const statusText = document.getElementById('apiStatusText');
            
            statusDot.className = 'status-dot offline';
            statusText.textContent = '连接失败';
        }
    }

    startPeriodicRefresh() {
        // 每5分钟检查一次API状态
        setInterval(() => {
            this.checkApiStatus();
        }, 300000);
    }

    async showImportantNotices() {
        const modal = document.getElementById('noticesModal');
        const container = document.getElementById('noticesList');
        
        if (!container) return;

        if (this.importantNotices && this.importantNotices.length > 0) {
            container.innerHTML = this.importantNotices.map(notice => `
                <div class="notice-item">
                    <div class="notice-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="notice-text">${notice}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-muted text-center">暂无重要提醒</div>';
        }

        Modal.show('noticesModal');
    }

    checkShowNotices() {
        // 检查是否需要自动显示重要提醒
        const today = new Date().toDateString();
        const lastShown = Storage.get('notices_last_shown');
        const dontShow = Storage.get('notices_dont_show_today');

        if (lastShown !== today && dontShow !== today) {
            // 延迟3秒显示，让页面加载完成
            setTimeout(() => {
                this.showImportantNotices();
                Storage.set('notices_last_shown', today);
            }, 3000);
        }
    }

    showUatUploadInfo() {
        Toast.info('UAT上传功能为预留接口，等待第三方平台对接后开放', 5000);
    }

    loadMoreHistory() {
        // 实现加载更多历史记录的逻辑
        Toast.info('加载更多功能开发中...');
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CrawlerApp();
});

// 处理不显示提醒的复选框
document.addEventListener('DOMContentLoaded', () => {
    const dontShowCheckbox = document.getElementById('dontShowAgain');
    if (dontShowCheckbox) {
        dontShowCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                const today = new Date().toDateString();
                Storage.set('notices_dont_show_today', today);
            } else {
                Storage.remove('notices_dont_show_today');
            }
        });
    }
});