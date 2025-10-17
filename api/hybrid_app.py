"""
混合架构应用 - Vercel前端 + 外部爬虫服务
支持通过API调用外部爬虫服务
"""

from flask import Flask, jsonify, request, render_template_string
import os
import sys
import json
import requests
from datetime import datetime
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# 扩展的HTML模板（支持文件上传和外部API）
HYBRID_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大众点评爬虫 - 混合部署版</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        .container { max-width: 1200px; margin-top: 20px; }
        .status-online { color: #28a745; }
        .status-offline { color: #dc3545; }
        .warning-banner {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .upload-area {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
            transition: all 0.3s;
        }
        .upload-area:hover {
            border-color: #007bff;
            background-color: #f8f9fa;
        }
        .api-config {
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">大众点评爬虫 Web应用</h1>

        <!-- 部署说明 -->
        <div class="alert alert-info">
            <strong>🌐 当前部署：</strong> Vercel Serverless + 外部API服务<br>
            <strong>📝 说明：</strong> Web界面运行在Vercel，爬虫功能通过外部API服务实现
        </div>

        <!-- API配置区域 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>🔧 外部API配置</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <label for="apiEndpoint" class="form-label">爬虫服务API地址</label>
                        <input type="text" class="form-control" id="apiEndpoint"
                               placeholder="http://your-crawler-server.com/api" value="">
                        <small class="text-muted">输入你的爬虫服务器API地址</small>
                    </div>
                    <div class="col-md-6">
                        <label for="apiKey" class="form-label">API密钥 (可选)</label>
                        <input type="password" class="form-control" id="apiKey"
                               placeholder="your-api-key">
                        <small class="text-muted">如果API需要认证，请输入密钥</small>
                    </div>
                </div>
                <button class="btn btn-primary mt-3" onclick="testExternalAPI()">测试API连接</button>
                <div id="apiTestResult" class="mt-3"></div>
            </div>
        </div>

        <!-- 爬虫任务配置 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>🚀 爬虫任务配置</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <label for="citySelect" class="form-label">选择城市</label>
                        <select class="form-select" id="citySelect">
                            <option value="">正在加载...</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label for="categorySelect" class="form-label">选择品类</label>
                        <select class="form-select" id="categorySelect" multiple>
                            <option value="">正在加载...</option>
                        </select>
                        <small class="text-muted">按住Ctrl多选，最多2个</small>
                    </div>
                    <div class="col-md-4">
                        <label for="pageRange" class="form-label">页数范围</label>
                        <input type="text" class="form-control" id="pageRange"
                               placeholder="1-15" value="1-15">
                    </div>
                </div>

                <!-- Cookie配置 -->
                <div class="row mt-3">
                    <div class="col-12">
                        <label for="cookieInput" class="form-label">大众点评Cookie</label>
                        <textarea class="form-control" id="cookieInput" rows="3"
                                  placeholder="请输入你的大众点评Cookie..."></textarea>
                        <small class="text-muted">
                            Cookie格式：_lxsdk_cuid=xxx; dper=xxx; ll=xxx; ...
                        </small>
                    </div>
                </div>

                <button class="btn btn-success mt-3" onclick="startCrawlerTask()">开始爬取</button>
                <button class="btn btn-warning mt-3" onclick="checkTaskStatus()">检查状态</button>
            </div>
        </div>

        <!-- 文件上传区域 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>📁 文件处理</h5>
            </div>
            <div class="card-body">
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <input type="file" id="fileInput" style="display: none;" accept=".csv,.xlsx" onchange="handleFileUpload(event)">
                    <p>📄 点击或拖拽文件到此处上传</p>
                    <p class="text-muted">支持CSV、Excel格式</p>
                </div>
                <div id="fileInfo" class="mt-3"></div>

                <!-- 高德API配置 -->
                <div class="api-config">
                    <h6>🗺️ 高德地图API配置</h6>
                    <div class="row">
                        <div class="col-md-8">
                            <input type="text" class="form-control" id="gaodeApiKey"
                                   placeholder="输入高德API Key">
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-info" onclick="processWithGaode()">使用高德API处理</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 任务状态 -->
        <div class="card">
            <div class="card-header">
                <h5>📊 任务状态</h5>
            </div>
            <div class="card-body">
                <div id="taskStatus">
                    <p class="text-muted">暂无任务</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 全局变量
        let currentTaskId = null;
        let cities = {};
        let categories = {};

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadConfigurations();
            setupDragAndDrop();
        });

        // 加载配置信息
        async function loadConfigurations() {
            try {
                // 加载城市配置
                const citiesResponse = await fetch('/api/config/cities');
                const citiesData = await citiesResponse.json();
                if (citiesData.success) {
                    cities = citiesData.data;
                    const citySelect = document.getElementById('citySelect');
                    citySelect.innerHTML = '<option value="">请选择城市</option>';
                    Object.keys(cities).forEach(city => {
                        const option = document.createElement('option');
                        option.value = cities[city];
                        option.textContent = city;
                        citySelect.appendChild(option);
                    });
                }

                // 加载品类配置
                const categoriesResponse = await fetch('/api/config/categories');
                const categoriesData = await categoriesResponse.json();
                if (categoriesData.success) {
                    categories = categoriesData.data;
                    const categorySelect = document.getElementById('categorySelect');
                    categorySelect.innerHTML = '';
                    Object.keys(categories).forEach(category => {
                        const option = document.createElement('option');
                        option.value = categories[category];
                        option.textContent = category;
                        categorySelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('加载配置失败:', error);
            }
        }

        // 设置拖拽上传
        function setupDragAndDrop() {
            const uploadArea = document.querySelector('.upload-area');

            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = '#007bff';
                uploadArea.style.backgroundColor = '#f8f9fa';
            });

            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = '#ccc';
                uploadArea.style.backgroundColor = '';
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.style.borderColor = '#ccc';
                uploadArea.style.backgroundColor = '';

                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileUpload({ target: { files: files } });
                }
            });
        }

        // 测试外部API连接
        async function testExternalAPI() {
            const endpoint = document.getElementById('apiEndpoint').value;
            const apiKey = document.getElementById('apiKey').value;
            const resultDiv = document.getElementById('apiTestResult');

            if (!endpoint) {
                resultDiv.innerHTML = '<div class="alert alert-warning">请输入API地址</div>';
                return;
            }

            try {
                const response = await axios.get(endpoint + '/status', {
                    headers: apiKey ? { 'Authorization': 'Bearer ' + apiKey } : {}
                });

                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✅ API连接成功</strong><br>
                        状态: ${JSON.stringify(response.data, null, 2)}
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>❌ API连接失败</strong><br>
                        错误: ${error.message}
                    </div>
                `;
            }
        }

        // 开始爬虫任务
        async function startCrawlerTask() {
            const endpoint = document.getElementById('apiEndpoint').value;
            const apiKey = document.getElementById('apiKey').value;
            const city = document.getElementById('citySelect').value;
            const categorySelect = document.getElementById('categorySelect');
            const selectedCategories = Array.from(categorySelect.selectedOptions).map(option => option.value);
            const pageRange = document.getElementById('pageRange').value;
            const cookie = document.getElementById('cookieInput').value;

            if (!endpoint) {
                alert('请先配置外部API地址');
                return;
            }

            if (!city || selectedCategories.length === 0) {
                alert('请选择城市和品类');
                return;
            }

            if (!cookie) {
                alert('请输入大众点评Cookie');
                return;
            }

            try {
                const response = await axios.post(endpoint + '/crawler/start', {
                    city: city,
                    categories: selectedCategories.slice(0, 2), // 最多2个品类
                    page_range: pageRange,
                    cookie: cookie
                }, {
                    headers: apiKey ? { 'Authorization': 'Bearer ' + apiKey } : {}
                });

                if (response.data.success) {
                    currentTaskId = response.data.task_id;
                    updateTaskStatus('任务已启动，任务ID: ' + currentTaskId);

                    // 开始定期检查状态
                    setInterval(checkTaskStatus, 5000);
                } else {
                    alert('启动任务失败: ' + response.data.message);
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }

        // 检查任务状态
        async function checkTaskStatus() {
            if (!currentTaskId) return;

            const endpoint = document.getElementById('apiEndpoint').value;
            const apiKey = document.getElementById('apiKey').value;

            try {
                const response = await axios.get(endpoint + '/crawler/status/' + currentTaskId, {
                    headers: apiKey ? { 'Authorization': 'Bearer ' + apiKey } : {}
                });

                updateTaskStatus('任务状态: ' + JSON.stringify(response.data, null, 2));
            } catch (error) {
                console.error('检查状态失败:', error);
            }
        }

        // 更新任务状态显示
        function updateTaskStatus(status) {
            document.getElementById('taskStatus').innerHTML = `
                <div class="alert alert-info">
                    <strong>任务状态:</strong><br>
                    <pre>${status}</pre>
                </div>
            `;
        }

        // 处理文件上传
        function handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            const fileInfo = document.getElementById('fileInfo');
            fileInfo.innerHTML = `
                <div class="alert alert-success">
                    <strong>已选择文件:</strong> ${file.name} (${(file.size / 1024).toFixed(2)} KB)<br>
                    <small>文件已准备处理</small>
                </div>
            `;
        }

        // 使用高德API处理
        async function processWithGaode() {
            const endpoint = document.getElementById('apiEndpoint').value;
            const apiKey = document.getElementById('apiKey').value;
            const gaodeKey = document.getElementById('gaodeApiKey').value;
            const fileInput = document.getElementById('fileInput');

            if (!endpoint) {
                alert('请先配置外部API地址');
                return;
            }

            if (!fileInput.files.length) {
                alert('请先上传文件');
                return;
            }

            if (!gaodeKey) {
                alert('请输入高德API Key');
                return;
            }

            // 这里应该实现文件上传到外部API的逻辑
            alert('文件处理功能需要在外部API服务中实现');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页"""
    return render_template_string(HYBRID_HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'running',
        'environment': 'vercel-hybrid',
        'timestamp': datetime.now().isoformat(),
        'features': {
            'web_interface': True,
            'external_api_support': True,
            'file_upload': True,
            'crawler': 'external_api_required'
        },
        'message': '混合版本 - 支持外部API调用'
    })

@app.route('/api/config/cities')
def get_cities():
    """获取城市配置"""
    try:
        from config.crawler_config import CITIES
        return jsonify({
            'success': True,
            'data': CITIES,
            'count': len(CITIES)
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Configuration not available'
        }), 500

@app.route('/api/config/categories')
def get_categories():
    """获取品类配置"""
    try:
        from config.crawler_config import CATEGORIES
        return jsonify({
            'success': True,
            'data': CATEGORIES,
            'count': len(CATEGORIES)
        })
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Configuration not available'
        }), 500

@app.route('/api/crawler/start', methods=['POST'])
def start_crawler():
    """代理爬虫启动请求到外部API"""
    data = request.get_json()

    # 这里可以实现对外部API的代理调用
    return jsonify({
        'success': False,
        'error': 'Direct crawler functionality requires external API service',
        'message': 'Please configure external crawler service and use the web interface',
        'received_data': data
    }), 503

# Vercel serverless handler
def handler(environ, start_response):
    """Vercel serverless function handler"""
    return app(environ, start_response)

# 如果直接运行此文件（用于本地测试）
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)