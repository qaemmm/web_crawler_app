"""
任务队列和状态管理器
"""

import uuid
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
from ..models.database import DatabaseManager
from ..core.custom_crawler import WebCustomCrawler

# 配置日志
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, db_manager: DatabaseManager, cookie_manager, max_concurrent_tasks: int = 1):
        self.db_manager = db_manager
        self.cookie_manager = cookie_manager  # 添加CookieManager引用
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = {}  # task_id -> task_info
        self.task_status_callbacks = {}  # task_id -> callback_function
        self.worker_thread = None
        self.is_running = False
        self._lock = threading.Lock()
    
    def start_worker(self):
        """启动任务处理工作线程"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def stop_worker(self, timeout=10):
        """停止任务处理工作线程 - 优化版本"""
        logger.info("开始停止任务队列工作线程...")
        
        # 设置停止标志
        self.is_running = False
        
        # 等待当前运行的任务完成
        if self.running_tasks:
            logger.info(f"等待 {len(self.running_tasks)} 个正在运行的任务完成...")
            wait_start = time.time()
            
            while self.running_tasks and (time.time() - wait_start) < timeout:
                time.sleep(0.5)
            
            if self.running_tasks:
                logger.warning(f"超时后仍有 {len(self.running_tasks)} 个任务未完成")
        
        # 停止工作线程
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("正在停止工作线程...")
            self.worker_thread.join(timeout=5)
            
            if self.worker_thread.is_alive():
                logger.warning("工作线程未能在超时时间内停止")
            else:
                logger.info("工作线程已成功停止")
        
        # 清理资源
        self.task_status_callbacks.clear()
        self.running_tasks.clear()
        
        logger.info("任务队列工作线程停止完成")
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.is_running:
            try:
                if len(self.running_tasks) < self.max_concurrent_tasks:
                    # 获取下一个待处理任务
                    task = self._get_next_task()
                    if task:
                        self._execute_task(task)
                
                time.sleep(1)  # 避免CPU占用过高
                
            except Exception as e:
                print(f"任务队列工作线程异常: {e}")
                time.sleep(5)
    
    def _get_next_task(self) -> Optional[Dict]:
        """获取下一个待处理任务"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM task_queue 
                    WHERE status = 'pending' 
                    ORDER BY priority DESC, created_at ASC 
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    task = dict(zip(columns, row))
                    
                    # 更新任务状态为队列中
                    cursor.execute('''
                        UPDATE task_queue 
                        SET status = 'queued', updated_at = ? 
                        WHERE task_id = ?
                    ''', (datetime.now(), task['task_id']))
                    
                    conn.commit()
                    return task
                
                return None
                
        except Exception as e:
            print(f"获取下一个任务失败: {e}")
            return None
    
    def _execute_task(self, task: Dict):
        """执行单个任务"""
        task_id = task['task_id']
        logger.info(f"开始执行任务: {task_id}")
        
        try:
            with self._lock:
                self.running_tasks[task_id] = {
                    'task': task,
                    'start_time': datetime.now(),
                    'status': TaskStatus.RUNNING
                }
            
            # 更新数据库状态
            self.db_manager.update_crawl_history(task_id, status='running')
            self._notify_status_change(task_id, TaskStatus.RUNNING, "任务开始执行")
            logger.info(f"任务 {task_id} 状态已更新为运行中")
            
            # 解析任务参数
            import json
            categories = json.loads(task['categories'])
            logger.info(f"任务 {task_id} 参数解析完成: 城市={task['city']}, 品类={categories}")
            
            # 创建状态回调函数
            def status_callback(status_info):
                self._notify_status_change(task_id, TaskStatus.RUNNING, status_info['message'], status_info)
            
            # 创建爬虫实例并执行任务
            logger.info(f"任务 {task_id} 创建爬虫实例")
            crawler = WebCustomCrawler(task['cookie_string'], status_callback)
            
            # 将英文城市代码转换为中文名
            city_name = None
            for name, code in crawler.cities.items():
                if code == task['city']:
                    city_name = name
                    break
            
            if not city_name:
                error_msg = f"不支持的城市代码: {task['city']}"
                logger.error(f"任务 {task_id} 失败: {error_msg}")
                raise Exception(error_msg)
            
            logger.info(f"任务 {task_id} 城市转换成功: {task['city']} -> {city_name}")
            
            # 将品类ID转换为中文品类名
            category_names = []
            for category_id in categories:
                category_name = None
                for name, cid in crawler.categories.items():
                    if cid == category_id:
                        category_name = name
                        break
                if category_name:
                    category_names.append(category_name)
                else:
                    error_msg = f"不支持的品类ID: {category_id}"
                    logger.error(f"任务 {task_id} 失败: {error_msg}")
                    raise Exception(error_msg)
            
            logger.info(f"任务 {task_id} 品类转换成功: {categories} -> {category_names}")
            
            # 使用修正后的方法调用
            start_page = task.get('start_page', 1)
            end_page = task.get('end_page', 15)
            logger.info(f"任务 {task_id} 开始爬取: 城市={city_name}, 品类={category_names}, 页数范围={start_page}-{end_page}")
            result = crawler.crawl_specific_task(
                city_name,  # 使用中文城市名
                category_names,  # 使用中文品类名列表
                start_page,  # 起始页
                end_page   # 结束页
            )
            
            # 处理新的返回值格式
            if len(result) == 3:
                success, data, saved_files = result
            else:
                success, data = result
                saved_files = []
            
            logger.info(f"任务 {task_id} 爬取完成: 成功={success}, 数据量={len(data) if data else 0}, 保存文件={len(saved_files)}")
            
            if success:
                # 保存数据
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                from config.crawler_config import FILE_PATHS
                save_result = crawler.save_task_data(
                    data, 
                    city_name,  # 使用中文城市名
                    category_names,  # 使用中文品类名列表
                    FILE_PATHS['OUTPUTS_DIR']
                )
                
                # 更新数据库（使用中文名称）
                self.db_manager.update_crawl_history(
                    task_id,
                    status='completed',
                    end_time=datetime.now(),
                    total_shops=len(data),
                    captcha_count=crawler.captcha_count,
                    skipped_pages=crawler.skipped_pages,
                    output_file=save_result['filename'] if save_result else None
                )
                
                # 记录爬取组合（使用中文名称）
                cookie_hash = self.cookie_manager.hash_cookie(task['cookie_string'])
                for category_name in category_names:
                    category_data = [d for d in data if d['secondary_category'] == category_name]
                    self.db_manager.record_crawl_combination(
                        city_name, category_name, cookie_hash, task_id, 
                        task.get('end_page', 15), len(category_data)
                    )
                
                self._notify_status_change(task_id, TaskStatus.COMPLETED, f"任务完成，共爬取 {len(data)} 个商铺")
                
            else:
                self.db_manager.update_crawl_history(
                    task_id,
                    status='failed',
                    end_time=datetime.now(),
                    error_message="爬取任务执行失败"
                )
                
                self._notify_status_change(task_id, TaskStatus.FAILED, "任务执行失败")
            
        except Exception as e:
            error_message = f"任务执行异常: {e}"
            logger.error(f"任务 {task_id} 执行失败: {error_message}", exc_info=True)
            
            self.db_manager.update_crawl_history(
                task_id,
                status='failed',
                end_time=datetime.now(),
                error_message=error_message
            )
            
            self._notify_status_change(task_id, TaskStatus.FAILED, error_message)
            
        finally:
            # 清理运行任务记录
            with self._lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
            
            # 更新任务队列状态
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM task_queue WHERE task_id = ?
                    ''', (task_id,))
                    conn.commit()
            except Exception as e:
                logger.error(f"清理任务队列记录失败: {e}")
    
    def _notify_status_change(self, task_id: str, status: TaskStatus, message: str, extra_info: Dict = None):
        """通知任务状态变化"""
        if task_id in self.task_status_callbacks:
            try:
                callback = self.task_status_callbacks[task_id]
                callback({
                    'task_id': task_id,
                    'status': status.value,
                    'message': message,
                    'timestamp': datetime.now().isoformat(),
                    'extra_info': extra_info or {}
                })
            except Exception as e:
                print(f"任务状态回调失败: {e}")
    
    def add_task(self, city: str, city_name: str, categories: List[str], category_names: List[str],
                 start_page: int = None, end_page: int = 15, range_type: str = 'first',
                 sort_type: str = 'popularity', cookie_string: str = '', priority: int = 0,
                 status_callback: Callable = None) -> str:
        """添加新任务到队列"""
        task_id = str(uuid.uuid4())
        
        try:
            # 添加到任务队列表
            import json
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO task_queue 
                    (task_id, city, categories, start_page, end_page, range_type, cookie_string, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                ''', (task_id, city, json.dumps(categories), start_page, end_page, range_type, cookie_string, priority))
                conn.commit()
            
            # 添加到爬取历史（使用中文名）
            cookie_hash = self.cookie_manager.hash_cookie(cookie_string)
            self.db_manager.add_crawl_history(task_id, city_name, category_names, start_page, end_page, range_type, cookie_hash)
            
            # 注册状态回调
            if status_callback:
                self.task_status_callbacks[task_id] = status_callback
            
            return task_id
            
        except Exception as e:
            print(f"添加任务失败: {e}")
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self._lock:
                # 如果任务正在运行，无法取消
                if task_id in self.running_tasks:
                    return False
            
            # 从队列中删除
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM task_queue WHERE task_id = ?', (task_id,))
                conn.commit()
            
            # 更新历史记录
            self.db_manager.update_crawl_history(
                task_id,
                status='cancelled',
                end_time=datetime.now()
            )
            
            self._notify_status_change(task_id, TaskStatus.CANCELLED, "任务已取消")
            return True
            
        except Exception as e:
            print(f"取消任务失败: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        try:
            # 检查是否在运行任务中
            with self._lock:
                if task_id in self.running_tasks:
                    running_task = self.running_tasks[task_id]
                    return {
                        'task_id': task_id,
                        'status': running_task['status'].value,
                        'start_time': running_task['start_time'].isoformat(),
                        'is_running': True
                    }
            
            # 检查队列中的任务
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_queue WHERE task_id = ?', (task_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    task = dict(zip(columns, row))
                    return {
                        'task_id': task_id,
                        'status': task['status'],
                        'created_at': task['created_at'],
                        'is_running': False
                    }
            
            # 检查历史记录
            history = self.db_manager.get_crawl_history(limit=1, offset=0)
            for record in history:
                if record['task_id'] == task_id:
                    return {
                        'task_id': task_id,
                        'status': record['status'],
                        'start_time': record['start_time'],
                        'end_time': record['end_time'],
                        'total_shops': record['total_shops'],
                        'is_running': False
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 队列中的任务数
                cursor.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'pending'")
                pending_tasks = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'queued'")
                queued_tasks = cursor.fetchone()[0]
            
            with self._lock:
                running_tasks = len(self.running_tasks)
            
            return {
                'pending_tasks': pending_tasks,
                'queued_tasks': queued_tasks,
                'running_tasks': running_tasks,
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'worker_running': self.is_running
            }
            
        except Exception as e:
            print(f"获取队列状态失败: {e}")
            return {}
    
    def remove_status_callback(self, task_id: str):
        """移除任务状态回调"""
        if task_id in self.task_status_callbacks:
            del self.task_status_callbacks[task_id]