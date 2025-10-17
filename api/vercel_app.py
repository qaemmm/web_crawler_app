"""
Vercel专用简化版Flask应用
由于Vercel serverless环境的限制，移除了Playwright爬虫功能
保留Web界面和基础API功能
"""

from flask import Flask, jsonify, request, render_template_string
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# 基础HTML模板（用于Web界面）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大众点评爬虫 Web应用</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
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
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center mb-4">大众点评爬虫 Web应用</h1>

        <div class="alert alert-info">
            <strong>⚠️ 部署提示：</strong> 当前应用运行在Vercel serverless环境中，爬虫功能已被禁用。
            如需使用完整爬虫功能，请在本地环境中运行。
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>应用状态</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>状态：</strong> <span class="status-online">在线</span></p>
                        <p><strong>部署环境：</strong> Vercel Serverless</p>
                        <p><strong>版本：</strong> 简化版</p>
                        <p><strong>当前时间：</strong> <span id="current-time"></span></p>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>API测试</h5>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary me-2" onclick="testAPI('/api/status')">测试状态</button>
                        <button class="btn btn-secondary" onclick="testAPI('/api/config/cities')">获取城市</button>
                        <div id="api-result" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>功能说明</h5>
                    </div>
                    <div class="card-body">
                        <h6>当前版本功能：</h6>
                        <ul>
                            <li>✅ Web界面展示</li>
                            <li>✅ 基础API接口</li>
                            <li>✅ 配置信息获取</li>
                            <li>❌ 网页爬虫功能（需要本地环境）</li>
                            <li>❌ Playwright浏览器自动化（Vercel不支持）</li>
                            <li>❌ 文件上传下载（serverless限制）</li>
                        </ul>

                        <h6>本地部署说明：</h6>
                        <p>要使用完整的爬虫功能，请在本地环境运行：</p>
                        <pre><code>git clone [repository]
cd web_crawler_app
pip install -r requirements.txt
playwright install chromium
python backend/app.py</code></pre>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 更新当前时间
        function updateTime() {
            document.getElementById('current-time').textContent = new Date().toLocaleString();
        }
        updateTime();
        setInterval(updateTime, 1000);

        // API测试功能
        async function testAPI(endpoint) {
            const resultDiv = document.getElementById('api-result');
            resultDiv.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';

            try {
                const response = await fetch(endpoint);
                const data = await response.json();
                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        <h6>API响应 (${endpoint}):</h6>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    </div>
                `;
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <h6>API错误:</h6>
                        <pre>${error.message}</pre>
                    </div>
                `;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'running',
        'environment': 'vercel-serverless',
        'timestamp': datetime.now().isoformat(),
        'features': {
            'web_interface': True,
            'crawler': False,
            'playwright': False,
            'file_upload': False
        },
        'message': '简化版本运行在Vercel serverless环境'
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
    """禁用的爬虫启动接口"""
    return jsonify({
        'success': False,
        'error': 'Crawler functionality is not available in Vercel serverless environment',
        'message': 'Please run the application locally to use crawler features'
    }), 503

# Vercel serverless handler
def handler(environ, start_response):
    """Vercel serverless function handler"""
    return app(environ, start_response)

# 如果直接运行此文件（用于本地测试）
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)