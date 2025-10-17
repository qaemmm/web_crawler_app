"""
Flask主应用入口
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import logging
import time
import threading
from datetime import datetime

# 导入配置和模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.crawler_config import WEB_CONFIG, FILE_PATHS, DATABASE_CONFIG
from backend.models.database import DatabaseManager
from backend.models.cookie_manager import CookieManager
from backend.core.task_queue import TaskQueue
# 这些蓝图将通过模块导入获取

# 创建Flask应用
app = Flask(__name__, 
           template_folder='../frontend',
           static_folder='../frontend/static')

# 配置应用
app.config.update(WEB_CONFIG)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(FILE_PATHS['LOGS_DIR'], 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建目录
for path in FILE_PATHS.values():
    os.makedirs(path, exist_ok=True)

# 初始化组件
db_manager = DatabaseManager(DATABASE_CONFIG['DB_PATH'])
cookie_manager = CookieManager(FILE_PATHS['COOKIES_DIR'], db_manager)
task_queue = TaskQueue(db_manager, cookie_manager)  # 传入CookieManager

# 启动任务队列工作线程
task_queue.start_worker()

# 导入API蓝图并注入依赖
from backend.api import crawler_api, config_api, upload_api, gaode_api, third_party_api

crawler_api.db_manager = db_manager
crawler_api.cookie_manager = cookie_manager  
crawler_api.task_queue = task_queue

config_api.db_manager = db_manager
config_api.cookie_manager = cookie_manager

upload_api.db_manager = db_manager

# 注册蓝图
app.register_blueprint(crawler_api.crawler_bp, url_prefix='/api/crawler')
app.register_blueprint(config_api.config_bp, url_prefix='/api/config')
app.register_blueprint(upload_api.upload_bp, url_prefix='/api/upload')
app.register_blueprint(gaode_api.gaode_bp, url_prefix='/api/gaode')
app.register_blueprint(third_party_api.third_party_bp, url_prefix='/api/third-party')

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'database': os.path.exists(DATABASE_CONFIG['DB_PATH']),
            'task_queue': task_queue.is_running,
            'cookie_manager': len(cookie_manager.list_cookies()) > 0
        }
    })

@app.route('/api/stats/dashboard')
def dashboard_stats():
    """仪表板统计信息"""
    try:
        crawl_stats = db_manager.get_crawl_stats()
        cookie_stats = cookie_manager.get_cookie_stats()
        queue_stats = task_queue.get_queue_status()
        
        return jsonify({
            'success': True,
            'data': {
                'crawl_stats': crawl_stats,
                'cookie_stats': cookie_stats,
                'queue_stats': queue_stats,
                'updated_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"获取仪表板统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/downloads/<filename>')
def download_file(filename):
    """下载爬取结果文件"""
    try:
        return send_from_directory(FILE_PATHS['OUTPUTS_DIR'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({'error': '文件不存在或下载失败'}), 404

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"服务器内部错误: {error}")
    return jsonify({'error': '服务器内部错误'}), 500

# 应用关闭时清理资源
@app.teardown_appcontext
def cleanup(error):
    """清理资源"""
    if error:
        logger.error(f"请求处理异常: {error}")

# 全局关停标志
_shutdown_in_progress = False
_shutdown_lock = threading.Lock()

def cleanup_on_exit():
    """应用退出时清理 - 优化版本"""
    global _shutdown_in_progress
    
    # 防止重复执行关停逻辑
    with _shutdown_lock:
        if _shutdown_in_progress:
            logger.info("关停已在进行中，跳过重复执行")
            return
        _shutdown_in_progress = True
    
    logger.info("正在关闭应用...")
    shutdown_start_time = time.time()
    
    try:
        # 1. 首先停止任务队列工作线程（最重要）
        if 'task_queue' in globals() and task_queue:
            logger.info("正在停止任务队列...")
            try:
                # 设置停止标志
                task_queue.is_running = False
                
                # 等待当前运行的任务完成或超时
                max_wait_time = 10  # 最多等待10秒
                wait_start = time.time()
                
                while task_queue.running_tasks and (time.time() - wait_start) < max_wait_time:
                    logger.info(f"等待 {len(task_queue.running_tasks)} 个任务完成...")
                    time.sleep(1)
                
                # 强制停止工作线程
                if task_queue.worker_thread and task_queue.worker_thread.is_alive():
                    logger.info("正在强制停止工作线程...")
                    task_queue.worker_thread.join(timeout=5)
                    
                    if task_queue.worker_thread.is_alive():
                        logger.warning("工作线程未能在超时时间内停止")
                    else:
                        logger.info("工作线程已成功停止")
                
                logger.info("任务队列已停止")
                
            except Exception as e:
                logger.error(f"停止任务队列时出错: {e}")
        
        # 2. 关闭数据库连接
        if 'db_manager' in globals() and db_manager:
            logger.info("正在关闭数据库连接...")
            try:
                db_manager.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接时出错: {e}")
        
        # 3. 清理其他资源
        try:
            # 清理任务状态回调
            if 'task_queue' in globals() and task_queue:
                task_queue.task_status_callbacks.clear()
                task_queue.running_tasks.clear()
        except Exception as e:
            logger.warning(f"清理任务队列资源时出错: {e}")
        
        shutdown_time = time.time() - shutdown_start_time
        logger.info(f"应用已安全关闭 (耗时: {shutdown_time:.2f}秒)")
        
    except Exception as e:
        logger.error(f"应用关闭时出错: {e}")
    finally:
        # 确保日志处理器被正确关闭
        try:
            # 给日志一点时间写入
            time.sleep(0.1)
            logging.shutdown()
        except Exception as e:
            print(f"关闭日志处理器时出错: {e}")

import atexit
import signal
import sys

# 信号处理函数
def signal_handler(signum, frame):
    """处理系统信号，优雅关闭应用"""
    logger.info(f"收到信号 {signum}，正在优雅关闭应用...")
    cleanup_on_exit()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
if hasattr(signal, 'SIGBREAK'):  # Windows特有信号
    signal.signal(signal.SIGBREAK, signal_handler)

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    logger.info("启动大众点评爬虫Web应用 (默认禁用热重载)...")
    logger.info(f"访问地址: http://{WEB_CONFIG['HOST']}:{WEB_CONFIG['PORT']}")
    logger.info("热重载已禁用，避免重复爬取问题")
    
    try:
        app.run(
            host=WEB_CONFIG['HOST'],
            port=WEB_CONFIG['PORT'],
            debug=True,  # 保持调试模式，但禁用重载
            use_reloader=False,  # 关键：禁用热重载
            threaded=WEB_CONFIG['THREADED']
        )
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception as e:
        logger.error(f"应用运行异常: {e}")
    finally:
        cleanup_on_exit()