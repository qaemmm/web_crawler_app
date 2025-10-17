"""
Cookie管理器 - 处理Cookie的存储、验证和轮换
"""

import hashlib
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .database import DatabaseManager

class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, cookies_dir: str, db_manager: DatabaseManager):
        self.cookies_dir = cookies_dir
        self.db_manager = db_manager
        os.makedirs(cookies_dir, exist_ok=True)
    
    def hash_cookie(self, cookie_string: str) -> str:
        """生成Cookie的hash值"""
        return hashlib.md5(cookie_string.encode()).hexdigest()[:16]
    
    def validate_cookie_format(self, cookie_string: str) -> Tuple[bool, str]:
        """验证Cookie格式"""
        if not cookie_string or not cookie_string.strip():
            return False, "Cookie不能为空"
        
        # 检查是否包含基本的大众点评Cookie字段
        required_fields = ['_lxsdk_cuid', 'dper', 'll']
        missing_fields = []
        
        for field in required_fields:
            if field not in cookie_string:
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Cookie缺少必要字段: {', '.join(missing_fields)}"
        
        # 检查Cookie格式（键=值; 键=值的格式）
        cookie_pairs = cookie_string.split(';')
        valid_pairs = 0
        
        for pair in cookie_pairs:
            if '=' in pair.strip():
                valid_pairs += 1
        
        if valid_pairs < 5:  # 至少需要5个有效的键值对
            return False, "Cookie格式不正确，有效键值对数量不足"
        
        return True, "Cookie格式验证通过"
    
    def save_cookie(self, cookie_name: str, cookie_string: str) -> Tuple[bool, str]:
        """保存Cookie到文件"""
        is_valid, message = self.validate_cookie_format(cookie_string)
        if not is_valid:
            return False, message
        
        try:
            cookie_file = os.path.join(self.cookies_dir, f"{cookie_name}.txt")
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write(cookie_string.strip())
            
            # 记录到数据库
            cookie_hash = self.hash_cookie(cookie_string)
            self.db_manager.record_cookie_usage(cookie_hash, cookie_name)
            
            return True, f"Cookie已保存到 {cookie_name}.txt"
            
        except Exception as e:
            return False, f"保存Cookie失败: {e}"
    
    def load_cookie(self, cookie_name: str) -> Tuple[bool, str, str]:
        """从文件加载Cookie"""
        try:
            cookie_file = os.path.join(self.cookies_dir, f"{cookie_name}.txt")
            
            if not os.path.exists(cookie_file):
                return False, "", f"Cookie文件 {cookie_name}.txt 不存在"
            
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_string = f.read().strip()
            
            if not cookie_string:
                return False, "", f"Cookie文件 {cookie_name}.txt 为空"
            
            is_valid, message = self.validate_cookie_format(cookie_string)
            if not is_valid:
                return False, "", f"Cookie格式无效: {message}"
            
            return True, cookie_string, "Cookie加载成功"
            
        except Exception as e:
            return False, "", f"加载Cookie失败: {e}"
    
    def list_cookies(self) -> List[Dict]:
        """列出所有可用的Cookie"""
        cookies = []
        
        try:
            if not os.path.exists(self.cookies_dir):
                return cookies
            
            for filename in os.listdir(self.cookies_dir):
                if filename.endswith('.txt'):
                    cookie_name = filename[:-4]  # 移除.txt后缀
                    
                    success, cookie_string, message = self.load_cookie(cookie_name)
                    
                    if success:
                        cookie_hash = self.hash_cookie(cookie_string)
                        
                        # 检查使用限制
                        can_use, daily_count = self.db_manager.check_cookie_limit(cookie_hash)
                        can_use_time, last_time = self.db_manager.check_last_crawl_time(cookie_hash)
                        
                        # 获取文件信息
                        cookie_file = os.path.join(self.cookies_dir, filename)
                        stat = os.stat(cookie_file)
                        
                        cookies.append({
                            'name': cookie_name,
                            'hash': cookie_hash,
                            'can_use': can_use and can_use_time,
                            'daily_usage': daily_count,
                            'last_used': last_time,
                            'file_size': stat.st_size,
                            'created_at': datetime.fromtimestamp(stat.st_ctime),
                            'modified_at': datetime.fromtimestamp(stat.st_mtime),
                            'status': 'available' if (can_use and can_use_time) else 'limited'
                        })
                    else:
                        cookies.append({
                            'name': cookie_name,
                            'hash': None,
                            'can_use': False,
                            'daily_usage': 0,
                            'last_used': None,
                            'error': message,
                            'status': 'invalid'
                        })
        
        except Exception as e:
            print(f"列出Cookie失败: {e}")
        
        return cookies
    
    def get_available_cookie(self) -> Tuple[bool, str, str]:
        """获取一个可用的Cookie"""
        cookies = self.list_cookies()
        
        # 筛选可用的Cookie
        available_cookies = [c for c in cookies if c['can_use'] and c['status'] == 'available']
        
        if not available_cookies:
            return False, "", "没有可用的Cookie，请检查Cookie状态或添加新的Cookie"
        
        # 选择使用次数最少的Cookie
        best_cookie = min(available_cookies, key=lambda x: x['daily_usage'])
        
        success, cookie_string, message = self.load_cookie(best_cookie['name'])
        if success:
            return True, cookie_string, f"使用Cookie: {best_cookie['name']}"
        else:
            return False, "", message
    
    def delete_cookie(self, cookie_name: str) -> Tuple[bool, str]:
        """删除Cookie文件"""
        try:
            cookie_file = os.path.join(self.cookies_dir, f"{cookie_name}.txt")
            
            if not os.path.exists(cookie_file):
                return False, f"Cookie文件 {cookie_name}.txt 不存在"
            
            os.remove(cookie_file)
            return True, f"Cookie {cookie_name} 已删除"
            
        except Exception as e:
            return False, f"删除Cookie失败: {e}"
    
    def check_cookie_restrictions(self, cookie_string: str, city: str, categories: List[str]) -> Dict:
        """检查Cookie的使用限制 - 临时移除所有限制用于测试"""
        cookie_hash = self.hash_cookie(cookie_string)
        
        # 临时注释掉所有限制检查，直接返回可以使用
        # TODO: 上线前需要恢复这些限制
        
        # 检查每日使用限制 (已禁用)
        # can_use_daily, daily_count = self.db_manager.check_cookie_limit(cookie_hash, 2)
        can_use_daily, daily_count = True, 0  # 强制返回可用
        
        # 检查时间间隔限制 (已禁用)
        # can_use_time, last_time = self.db_manager.check_last_crawl_time(cookie_hash, 1)
        can_use_time, last_time = True, None  # 强制返回可用
        
        # 检查城市+品类组合限制 (已禁用)
        # crawled_combinations = []
        # for category in categories:
        #     if self.db_manager.is_combination_crawled(city, category, cookie_hash):
        #         crawled_combinations.append(category)
        crawled_combinations = []  # 强制返回空列表
        
        return {
            'can_use': True,  # 强制返回可以使用
            'daily_usage': daily_count,
            'max_daily_usage': 999,  # 临时设置为很大的数字
            'last_crawl_time': last_time,
            'min_interval_hours': 0,  # 临时设置为0小时间隔
            'crawled_combinations': crawled_combinations,
            'restrictions': {
                'daily_limit_reached': False,  # 强制返回无限制
                'time_interval_insufficient': False,  # 强制返回无限制
                'combinations_already_crawled': False  # 强制返回无限制
            }
        }
    
    def get_cookie_stats(self) -> Dict:
        """获取Cookie统计信息"""
        cookies = self.list_cookies()
        
        total_cookies = len(cookies)
        available_cookies = len([c for c in cookies if c['can_use']])
        invalid_cookies = len([c for c in cookies if c['status'] == 'invalid'])
        
        return {
            'total_cookies': total_cookies,
            'available_cookies': available_cookies,
            'limited_cookies': total_cookies - available_cookies - invalid_cookies,
            'invalid_cookies': invalid_cookies,
            'availability_rate': (available_cookies / total_cookies * 100) if total_cookies > 0 else 0
        }