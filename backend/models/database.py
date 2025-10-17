"""
数据库模型 - 爬取历史记录和任务管理
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建爬取历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    city TEXT NOT NULL,
                    categories TEXT NOT NULL,  -- JSON格式存储多个品类
                    start_page INTEGER DEFAULT 1,
                    end_page INTEGER NOT NULL,
                    range_type TEXT DEFAULT 'first',  -- first, last, custom
                    cookie_hash TEXT NOT NULL,  -- Cookie的hash值，用于识别账号
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    status TEXT NOT NULL,  -- pending, running, completed, failed
                    total_shops INTEGER DEFAULT 0,
                    captcha_count INTEGER DEFAULT 0,
                    skipped_pages INTEGER DEFAULT 0,
                    output_file TEXT,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建Cookie使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cookie_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookie_hash TEXT NOT NULL,
                    cookie_name TEXT,
                    last_used DATETIME NOT NULL,
                    daily_usage_count INTEGER DEFAULT 0,
                    usage_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cookie_hash, usage_date)
                )
            ''')
            
            # 创建爬取组合记录表（城市+品类+日期）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_combinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    category TEXT NOT NULL,
                    crawl_date DATE NOT NULL,
                    cookie_hash TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    pages_crawled INTEGER DEFAULT 0,
                    shops_found INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(city, category, crawl_date, cookie_hash)
                )
            ''')
            
            # 创建任务队列表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    city TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    start_page INTEGER DEFAULT 1,
                    end_page INTEGER NOT NULL,
                    range_type TEXT DEFAULT 'first',
                    cookie_string TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    scheduled_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def add_crawl_history(self, task_id: str, city: str, categories: List[str], 
                         start_page: int, end_page: int, range_type: str, cookie_hash: str) -> bool:
        """添加爬取历史记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO crawl_history 
                    (task_id, city, categories, start_page, end_page, range_type, cookie_hash, start_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (task_id, city, json.dumps(categories), start_page, end_page, range_type, cookie_hash, 
                      datetime.now(), 'pending'))
                conn.commit()
                return True
        except Exception as e:
            print(f"添加爬取历史失败: {e}")
            return False
    
    def update_crawl_history(self, task_id: str, **kwargs) -> bool:
        """更新爬取历史记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建更新SQL
                set_clauses = []
                values = []
                
                for key, value in kwargs.items():
                    if key in ['status', 'end_time', 'total_shops', 'captcha_count', 
                              'skipped_pages', 'output_file', 'error_message']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = ?")
                values.append(datetime.now())
                values.append(task_id)
                
                sql = f"UPDATE crawl_history SET {', '.join(set_clauses)} WHERE task_id = ?"
                cursor.execute(sql, values)
                conn.commit()
                return True
                
        except Exception as e:
            print(f"更新爬取历史失败: {e}")
            return False
    
    def record_cookie_usage(self, cookie_hash: str, cookie_name: str = None) -> bool:
        """记录Cookie使用情况"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().date()
                
                # 检查今天是否已有记录
                cursor.execute('''
                    SELECT daily_usage_count FROM cookie_usage 
                    WHERE cookie_hash = ? AND usage_date = ?
                ''', (cookie_hash, today))
                
                result = cursor.fetchone()
                
                if result:
                    # 更新使用次数
                    cursor.execute('''
                        UPDATE cookie_usage 
                        SET daily_usage_count = daily_usage_count + 1, 
                            last_used = ?,
                            cookie_name = COALESCE(?, cookie_name)
                        WHERE cookie_hash = ? AND usage_date = ?
                    ''', (datetime.now(), cookie_name, cookie_hash, today))
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO cookie_usage 
                        (cookie_hash, cookie_name, last_used, daily_usage_count, usage_date)
                        VALUES (?, ?, ?, 1, ?)
                    ''', (cookie_hash, cookie_name, datetime.now(), today))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"记录Cookie使用失败: {e}")
            return False
    
    def check_cookie_limit(self, cookie_hash: str, max_daily_usage: int = 2) -> tuple[bool, int]:
        """检查Cookie是否超过每日使用限制"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().date()
                
                cursor.execute('''
                    SELECT daily_usage_count FROM cookie_usage 
                    WHERE cookie_hash = ? AND usage_date = ?
                ''', (cookie_hash, today))
                
                result = cursor.fetchone()
                current_usage = result[0] if result else 0
                
                can_use = current_usage < max_daily_usage
                return can_use, current_usage
                
        except Exception as e:
            print(f"检查Cookie限制失败: {e}")
            return False, 0
    
    def check_last_crawl_time(self, cookie_hash: str, min_interval_hours: int = 1) -> tuple[bool, Optional[datetime]]:
        """检查上次爬取时间是否满足间隔要求"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT MAX(start_time) FROM crawl_history 
                    WHERE cookie_hash = ? AND status IN ('completed', 'running')
                ''', (cookie_hash,))
                
                result = cursor.fetchone()
                last_crawl_time = result[0] if result and result[0] else None
                
                if not last_crawl_time:
                    return True, None
                
                last_crawl_datetime = datetime.fromisoformat(last_crawl_time)
                time_diff = datetime.now() - last_crawl_datetime
                
                can_crawl = time_diff >= timedelta(hours=min_interval_hours)
                return can_crawl, last_crawl_datetime
                
        except Exception as e:
            print(f"检查爬取时间间隔失败: {e}")
            return True, None
    
    def is_combination_crawled(self, city: str, category: str, cookie_hash: str) -> bool:
        """检查城市+品类组合今天是否已被爬取"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().date()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM crawl_combinations 
                    WHERE city = ? AND category = ? AND crawl_date = ? AND cookie_hash = ?
                ''', (city, category, today, cookie_hash))
                
                result = cursor.fetchone()
                return result[0] > 0
                
        except Exception as e:
            print(f"检查爬取组合失败: {e}")
            return False
    
    def record_crawl_combination(self, city: str, category: str, cookie_hash: str, 
                               task_id: str, pages_crawled: int = 0, shops_found: int = 0) -> bool:
        """记录爬取组合"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().date()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO crawl_combinations 
                    (city, category, crawl_date, cookie_hash, task_id, pages_crawled, shops_found)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (city, category, today, cookie_hash, task_id, pages_crawled, shops_found))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"记录爬取组合失败: {e}")
            return False
    
    def get_crawl_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取爬取历史记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM crawl_history 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    record = dict(zip(columns, row))
                    # 解析JSON格式的categories
                    if record['categories']:
                        record['categories'] = json.loads(record['categories'])
                    results.append(record)
                
                return results
                
        except Exception as e:
            print(f"获取爬取历史失败: {e}")
            return []
    
    def get_crawl_stats(self) -> Dict:
        """获取爬取统计信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总任务数
                cursor.execute('SELECT COUNT(*) FROM crawl_history')
                total_tasks = cursor.fetchone()[0]
                
                # 今日任务数
                today = datetime.now().date()
                cursor.execute('''
                    SELECT COUNT(*) FROM crawl_history 
                    WHERE DATE(created_at) = ?
                ''', (today,))
                today_tasks = cursor.fetchone()[0]
                
                # 成功任务数
                cursor.execute("SELECT COUNT(*) FROM crawl_history WHERE status = 'completed'")
                completed_tasks = cursor.fetchone()[0]
                
                # 总商铺数
                cursor.execute('SELECT SUM(total_shops) FROM crawl_history WHERE total_shops IS NOT NULL')
                result = cursor.fetchone()
                total_shops = result[0] if result[0] else 0
                
                # 活跃Cookie数
                cursor.execute('''
                    SELECT COUNT(DISTINCT cookie_hash) FROM cookie_usage 
                    WHERE usage_date = ?
                ''', (today,))
                active_cookies = cursor.fetchone()[0]
                
                return {
                    'total_tasks': total_tasks,
                    'today_tasks': today_tasks,
                    'completed_tasks': completed_tasks,
                    'total_shops': total_shops,
                    'active_cookies': active_cookies,
                    'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                }
                
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # 清理旧的爬取历史
                cursor.execute('DELETE FROM crawl_history WHERE created_at < ?', (cutoff_date,))
                
                # 清理旧的Cookie使用记录
                cursor.execute('DELETE FROM cookie_usage WHERE usage_date < ?', (cutoff_date.date(),))
                
                # 清理旧的爬取组合记录
                cursor.execute('DELETE FROM crawl_combinations WHERE crawl_date < ?', (cutoff_date.date(),))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"清理旧记录失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        # SQLite使用连接池，每次操作都会自动打开和关闭连接
        # 这里主要是为了兼容性，实际上SQLite不需要显式关闭
        pass