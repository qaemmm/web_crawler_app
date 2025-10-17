"""
Vercel部署入口文件 - 适配serverless架构
"""

from flask import Flask, jsonify
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入原有的Flask应用
try:
    from backend.app import app
except ImportError as e:
    # 如果导入失败，创建一个简单的应用用于调试
    app = Flask(__name__)

    @app.route('/')
    def index():
        return jsonify({
            "error": "Application import failed",
            "message": str(e),
            "status": "debug_mode"
        })

    @app.route('/api/status')
    def status():
        return jsonify({
            "status": "debug_mode",
            "message": "Original app could not be imported"
        })

# Vercel serverless handler
def handler(environ, start_response):
    """Vercel serverless function handler"""
    return app(environ, start_response)

# 如果直接运行此文件（用于本地测试）
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)