/**
 * 工具函数集合
 */

// API基础URL
const API_BASE_URL = '';

/**
 * HTTP请求工具
 */
class ApiClient {
    static async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };

        const config = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(API_BASE_URL + url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API请求失败:', error);
            throw error;
        }
    }

    static async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl);
    }

    static async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async put(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async delete(url) {
        return this.request(url, {
            method: 'DELETE'
        });
    }
}

/**
 * 消息提示工具
 */
class Toast {
    static container = null;

    static init() {
        this.container = document.getElementById('toastContainer');
    }

    static show(message, type = 'info', duration = 5000) {
        if (!this.container) this.init();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        const titles = {
            success: '成功',
            error: '错误',
            warning: '警告',
            info: '提示'
        };

        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-title">
                    <i class="${icons[type]}"></i>
                    ${titles[type]}
                </div>
                <button class="toast-close">&times;</button>
            </div>
            <div class="toast-body">${message}</div>
        `;

        // 添加关闭事件
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            this.remove(toast);
        });

        this.container.appendChild(toast);

        // 自动关闭
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toast);
            }, duration);
        }

        return toast;
    }

    static remove(toast) {
        if (toast && toast.parentNode) {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }
    }

    static success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    static error(message, duration = 5000) {
        return this.show(message, 'error', duration);
    }

    static warning(message, duration = 4000) {
        return this.show(message, 'warning', duration);
    }

    static info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }
}

/**
 * 加载指示器工具
 */
class Loading {
    static overlay = null;

    static init() {
        this.overlay = document.getElementById('loadingOverlay');
    }

    static show(text = '处理中...') {
        if (!this.overlay) this.init();
        
        const textElement = this.overlay.querySelector('.loading-text');
        if (textElement) {
            textElement.textContent = text;
        }
        
        this.overlay.style.display = 'flex';
    }

    static hide() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
        }
    }
}

/**
 * 模态框工具
 */
class Modal {
    static show(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    static hide(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    static init() {
        // 为所有模态框添加点击外部关闭和ESC关闭功能
        document.querySelectorAll('.modal').forEach(modal => {
            // 点击外部关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hide(modal.id);
                }
            });

            // 关闭按钮
            const closeBtn = modal.querySelector('.modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.hide(modal.id);
                });
            }
        });

        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const visibleModal = document.querySelector('.modal.show');
                if (visibleModal) {
                    this.hide(visibleModal.id);
                }
            }
        });
    }
}

/**
 * 表单验证工具
 */
class Validator {
    static validateCookie(cookieString) {
        if (!cookieString || !cookieString.trim()) {
            return { valid: false, message: 'Cookie不能为空' };
        }

        // 检查基本格式
        const cookiePairs = cookieString.split(';');
        let validPairs = 0;

        for (const pair of cookiePairs) {
            if (pair.trim().includes('=')) {
                validPairs++;
            }
        }

        if (validPairs < 5) {
            return { valid: false, message: 'Cookie格式不正确，有效键值对数量不足' };
        }

        // 检查必要字段
        const requiredFields = ['_lxsdk_cuid', 'dper', 'll'];
        const missingFields = [];

        for (const field of requiredFields) {
            if (!cookieString.includes(field)) {
                missingFields.push(field);
            }
        }

        if (missingFields.length > 0) {
            return { 
                valid: false, 
                message: `Cookie缺少必要字段: ${missingFields.join(', ')}` 
            };
        }

        return { valid: true, message: 'Cookie格式验证通过' };
    }

    static validateForm(formData) {
        const errors = [];

        if (!formData.city) {
            errors.push('请选择城市');
        }

        if (!formData.categories || formData.categories.length === 0) {
            errors.push('请至少选择一个品类');
        }

        if (formData.categories && formData.categories.length > 2) {
            errors.push('最多只能选择2个品类');
        }

        if (!formData.cookie_string) {
            errors.push('请输入Cookie');
        }

        // 验证页数范围参数
        if (formData.range_type === 'custom') {
            const startPage = parseInt(formData.start_page);
            const endPage = parseInt(formData.end_page);
            
            if (!startPage || startPage < 1) {
                errors.push('起始页必须大于0');
            }
            
            if (!endPage || endPage < 1) {
                errors.push('结束页必须大于0');
            }
            
            if (startPage && endPage && startPage > endPage) {
                errors.push('起始页不能大于结束页');
            }
            
            if (endPage && endPage > 100) {
                errors.push('结束页不能超过100');
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
}

/**
 * 本地存储工具
 */
class Storage {
    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('存储数据失败:', error);
            return false;
        }
    }

    static get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (error) {
            console.error('读取数据失败:', error);
            return defaultValue;
        }
    }

    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('删除数据失败:', error);
            return false;
        }
    }

    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('清空数据失败:', error);
            return false;
        }
    }
}

/**
 * 时间格式化工具
 */
class DateUtils {
    static formatRelative(dateString) {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (seconds < 60) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;
        
        return this.formatDate(date);
    }

    static formatDate(date) {
        if (!date) return '-';
        
        if (typeof date === 'string') {
            date = new Date(date);
        }
        
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    static formatDuration(seconds) {
        if (!seconds || seconds < 0) return '-';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}小时${minutes}分钟`;
        } else if (minutes > 0) {
            return `${minutes}分钟${secs}秒`;
        } else {
            return `${secs}秒`;
        }
    }
}

/**
 * 文件大小格式化工具
 */
class FileUtils {
    static formatSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    static getFileExtension(filename) {
        return filename.split('.').pop().toLowerCase();
    }

    static downloadFile(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * 数字格式化工具
 */
class NumberUtils {
    static format(number) {
        if (number === null || number === undefined) return '-';
        return number.toLocaleString('zh-CN');
    }

    static formatPercentage(value, total) {
        if (!total || total === 0) return '0%';
        return Math.round((value / total) * 100) + '%';
    }
}

/**
 * 防抖和节流工具
 */
class Throttle {
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    static throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

/**
 * DOM工具
 */
class DOMUtils {
    static createElement(tag, className = '', innerHTML = '') {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (innerHTML) element.innerHTML = innerHTML;
        return element;
    }

    static setAttributes(element, attributes) {
        Object.keys(attributes).forEach(key => {
            element.setAttribute(key, attributes[key]);
        });
    }

    static empty(element) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    static show(element) {
        element.style.display = '';
    }

    static hide(element) {
        element.style.display = 'none';
    }

    static toggle(element) {
        if (element.style.display === 'none') {
            this.show(element);
        } else {
            this.hide(element);
        }
    }
}

// 导出到全局
window.ApiClient = ApiClient;
window.Toast = Toast;
window.Loading = Loading;
window.Modal = Modal;
window.Validator = Validator;
window.Storage = Storage;
window.DateUtils = DateUtils;
window.FileUtils = FileUtils;
window.NumberUtils = NumberUtils;
window.Throttle = Throttle;
window.DOMUtils = DOMUtils;