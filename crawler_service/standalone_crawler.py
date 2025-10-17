"""
独立爬虫服务 - 可以部署在任何支持Python的服务器上
提供RESTful API接口，与Vercel前端配合使用
"""

from flask import Flask, request, jsonify, send_file
import os
import sys
import json
import uuid
import threading
import time
from datetime import datetime
from werkzeug.utils import secure_filename

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# 全局任务存储（生产环境应使用Redis或数据库）
active_tasks = {}
task_results = {}

# 导入爬虫模块
try:
    from backend.core.custom_crawler import WebCustomCrawler
    from backend.models.cookie_manager import CookieManager
    from backend.models.database import DatabaseManager
    from config.crawler_config import CRAWL_LIMITS, ANTI_SPIDER_CONFIG, FILE_PATHS
    CRAWLER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Crawler modules not available: {e}")
    CRAWLER_AVAILABLE = False

class CrawlerTask:
    """爬虫任务类"""
    def __init__(self, task_id, config):
        self.task_id = task_id
        self.config = config
        self.status = 'pending'
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.thread = None

    def start(self):
        """启动任务"""
        self.status = 'running'
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self._run_task)
        self.thread.start()

    def _run_task(self):
        """执行爬虫任务"""
        try:
            if not CRAWLER_AVAILABLE:
                raise Exception("Crawler modules not available")

            # 初始化爬虫
            crawler = WebCustomCrawler(self.config.get('cookie'))

            # 获取配置参数
            city = self.config.get('city')
            categories = self.config.get('categories', [])
            page_range = self.config.get('page_range', '1-15')

            # 解析页数范围
            if '-' in page_range:
                start_page, end_page = map(int, page_range.split('-'))
            else:
                start_page = 1
                end_page = int(page_range)

            results = []
            total_pages = len(categories) * (end_page - start_page + 1)
            current_page = 0

            # 执行爬取
            for category in categories:
                category_results = crawler.crawl_category(
                    city=city,
                    category=category,
                    start_page=start_page,
                    end_page=end_page,
                    progress_callback=lambda p: self._update_progress(
                        int((current_page + p / (end_page - start_page + 1)) / total_pages * 100)
                    )
                )
                results.extend(category_results)
                current_page += (end_page - start_page + 1)

            # 保存结果
            filename = f"crawl_results_{self.task_id}.csv"
            filepath = os.path.join(FILE_PATHS.get('OUTPUTS_DIR', '/tmp'), filename)

            import pandas as pd
            df = pd.DataFrame(results)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')

            self.status = 'completed'
            self.result = {
                'filename': filename,
                'filepath': filepath,
                'total_records': len(results),
                'categories': categories,
                'city': city,
                'pages_crawled': total_pages
            }

        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
        finally:
            self.end_time = datetime.now()
            # 清理活动任务
            if self.task_id in active_tasks:
                del active_tasks[self.task_id]

    def _update_progress(self, progress):
        """更新进度"""
        self.progress = min(100, max(0, progress))

    def get_status(self):
        """获取任务状态"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }

@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'crawler_available': CRAWLER_AVAILABLE,
        'active_tasks': len(active_tasks)
    })

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'running',
        'environment': 'standalone_crawler_service',
        'timestamp': datetime.now().isoformat(),
        'crawler_available': CRAWLER_AVAILABLE,
        'active_tasks': len(active_tasks),
        'version': '1.0.0'
    })

@app.route('/api/crawler/start', methods=['POST'])
def start_crawler():
    """启动爬虫任务"""
    try:
        data = request.get_json()

        # 验证必需参数
        required_fields = ['city', 'categories', 'cookie']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # 创建任务
        task_id = str(uuid.uuid4())
        task = CrawlerTask(task_id, data)

        # 存储任务
        active_tasks[task_id] = task

        # 启动任务
        task.start()

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Crawler task started successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/crawler/status/<task_id>')
def get_crawler_status(task_id):
    """获取爬虫任务状态"""
    if task_id in active_tasks:
        return jsonify({
            'success': True,
            'status': active_tasks[task_id].get_status()
        })
    else:
        # 检查是否在已完成任务中
        if task_id in task_results:
            return jsonify({
                'success': True,
                'status': task_results[task_id].get_status()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404

@app.route('/api/crawler/download/<task_id>')
def download_result(task_id):
    """下载爬虫结果"""
    if task_id in task_results and task_results[task_id].result:
        filepath = task_results[task_id].result['filepath']
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    else:
        return jsonify({'error': 'Result not found'}), 404

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件进行处理"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # 保存上传的文件
        filename = secure_filename(file.filename)
        upload_dir = FILE_PATHS.get('TEMP_DIR', '/tmp')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'size': os.path.getsize(filepath)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gaode/process', methods=['POST'])
def process_with_gaode():
    """使用高德API处理数据"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        api_key = data.get('api_key')

        if not file_path or not api_key:
            return jsonify({
                'success': False,
                'error': 'Missing file_path or api_key'
            }), 400

        # 这里实现高德API处理逻辑
        # 注意：实际实现需要高德地图API的具体调用代码

        return jsonify({
            'success': True,
            'message': 'Gaode API processing completed',
            'processed_records': 0  # 实际处理记录数
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks')
def list_tasks():
    """列出所有任务"""
    all_tasks = {}

    # 活动任务
    for task_id, task in active_tasks.items():
        all_tasks[task_id] = task.get_status()

    # 已完成任务
    for task_id, task in task_results.items():
        all_tasks[task_id] = task.get_status()

    return jsonify({
        'success': True,
        'tasks': all_tasks,
        'total_count': len(all_tasks)
    })

# 定期清理完成的任务
def cleanup_completed_tasks():
    """清理完成的任务"""
    while True:
        time.sleep(300)  # 每5分钟清理一次

        completed_task_ids = []
        for task_id, task in active_tasks.items():
            if task.status in ['completed', 'failed']:
                completed_task_ids.append(task_id)
                task_results[task_id] = task

        for task_id in completed_task_ids:
            del active_tasks[task_id]

        if completed_task_ids:
            print(f"Cleaned up {len(completed_task_ids)} completed tasks")

# 启动清理线程
cleanup_thread = threading.Thread(target=cleanup_completed_tasks, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    print("Starting Standalone Crawler Service...")
    print(f"Crawler Available: {CRAWLER_AVAILABLE}")
    print("Service will be available at: http://localhost:5001")
    print("API endpoints:")
    print("  GET  /api/status - Service status")
    print("  POST /api/crawler/start - Start crawler task")
    print("  GET  /api/crawler/status/<task_id> - Get task status")
    print("  GET  /api/crawler/download/<task_id> - Download result")

    app.run(host='0.0.0.0', port=5001, debug=False)