"""
爬虫相关API端点
"""

from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime
import hashlib

crawler_bp = Blueprint('crawler', __name__)

# 这些将在app.py中注入
db_manager = None
cookie_manager = None
task_queue = None

@crawler_bp.route('/start', methods=['POST'])
def start_crawl():
    """开始爬取任务"""
    try:
        data = request.get_json()
        
        # 验证请求参数
        required_fields = ['city', 'categories', 'cookie_string']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'缺少必要参数: {field}'
                }), 400
        
        city = data['city']
        categories = data['categories']
        cookie_string = data['cookie_string']

        # 处理排序参数
        sort_type = data.get('sort_type', 'popularity')
        if sort_type not in ['popularity', 'reviews']:
            sort_type = 'popularity'  # 默认人气排序
        
        # 处理页数范围参数
        range_type = data.get('range_type', 'first')
        if range_type == 'custom':
            start_page = data.get('start_page', 1)
            end_page = data.get('end_page', 15)
            
            # 验证页数参数
            try:
                start_page = int(start_page) if start_page is not None else 1
                end_page = int(end_page) if end_page is not None else 15
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': '页数范围参数必须是有效数字'
                }), 400
                
            if start_page < 1 or end_page < 1 or start_page > end_page or end_page > 100:
                return jsonify({
                    'success': False,
                    'error': f'页数范围无效: {start_page}-{end_page}，请检查范围是否正确'
                }), 400
                
        elif range_type == 'first':
            start_page = data.get('start_page', 1)
            end_page = data.get('end_page', 15)
            try:
                start_page = int(start_page) if start_page is not None else 1
                end_page = int(end_page) if end_page is not None else 15
            except (ValueError, TypeError):
                start_page = 1
                end_page = 15
        elif range_type == 'last':
            # 后15页需要先获取总页数，这里暂时使用默认值
            page_count = data.get('page_count', 15)
            try:
                page_count = int(page_count) if page_count is not None else 15
            except (ValueError, TypeError):
                page_count = 15
            start_page = None  # 标记为需要动态计算
            end_page = page_count
        else:
            start_page = 1
            end_page = 15
        
        # 验证城市和品类
        from config.crawler_config import CITIES, CATEGORIES, CRAWL_LIMITS
        
        # 验证城市代码
        if city not in CITIES.values():  # 现在接收的是城市代码，不是中文名
            return jsonify({
                'success': False,
                'error': f'不支持的城市代码: {city}'
            }), 400
        
        # 获取城市中文名（用于显示和保存文件）
        city_name = None
        for name, code in CITIES.items():
            if code == city:
                city_name = name
                break
        
        if not city_name:
            return jsonify({
                'success': False,
                'error': f'无法找到城市代码对应的中文名: {city}'
            }), 400
        
        if not isinstance(categories, list) or len(categories) == 0:
            return jsonify({
                'success': False,
                'error': '请至少选择一个品类'
            }), 400
        
        if len(categories) > CRAWL_LIMITS['MAX_CATEGORIES_PER_TASK']:
            return jsonify({
                'success': False,
                'error': f'最多只能选择{CRAWL_LIMITS["MAX_CATEGORIES_PER_TASK"]}个品类'
            }), 400
        
        # 验证品类ID并获取中文名
        category_names = []
        for category_id in categories:
            if category_id not in CATEGORIES.values():  # 现在接收的是品类ID，不是中文名
                return jsonify({
                    'success': False,
                    'error': f'不支持的品类ID: {category_id}'
                }), 400
            
            # 获取品类中文名
            for name, cid in CATEGORIES.items():
                if cid == category_id:
                    category_names.append(name)
                    break
        
        # 验证Cookie格式
        is_valid, message = cookie_manager.validate_cookie_format(cookie_string)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Cookie格式无效: {message}'
            }), 400
        
        # 检查Cookie使用限制（使用中文名进行检查）
        restrictions = cookie_manager.check_cookie_restrictions(cookie_string, city_name, category_names)
        if not restrictions['can_use']:
            error_messages = []
            if restrictions['restrictions']['daily_limit_reached']:
                error_messages.append(f"今日使用次数已达上限 ({restrictions['daily_usage']}/{restrictions['max_daily_usage']})")
            if restrictions['restrictions']['time_interval_insufficient']:
                error_messages.append(f"距离上次爬取时间不足{restrictions['min_interval_hours']}小时")
            if restrictions['restrictions']['combinations_already_crawled']:
                error_messages.append(f"以下组合今日已爬取: {', '.join(restrictions['crawled_combinations'])}")
            
            return jsonify({
                'success': False,
                'error': '爬取限制检查失败',
                'restrictions': restrictions,
                'error_messages': error_messages
            }), 400
        
        # 创建任务（传递城市代码和品类ID给爬虫，传递中文名给数据库）
        task_id = task_queue.add_task(
            city=city,  # 城市代码，如 'xian'
            city_name=city_name,  # 城市中文名，如 '西安'
            categories=categories,  # 品类ID列表，如 ['g34351']
            category_names=category_names,  # 品类中文名列表，如 ['地方菜系']
            start_page=start_page,
            end_page=end_page,
            range_type=range_type,
            sort_type=sort_type,  # 添加排序参数
            cookie_string=cookie_string,
            priority=1
        )
        
        # 创建任务数据记录
        task_data = {
            'task_id': task_id,
            'city': city,
            'categories': categories,
            'cookie_string': cookie_string,
            'start_page': start_page,
            'end_page': end_page,
            'range_type': range_type,
            'created_at': datetime.now().isoformat()
        }
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': '创建任务失败'
            }), 500
        
        # 记录Cookie使用
        cookie_hash = cookie_manager.hash_cookie(cookie_string)
        cookie_manager.db_manager.record_cookie_usage(cookie_hash)
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'city': city_name,  # 返回中文名供前端显示
                'categories': category_names,  # 返回中文名供前端显示
                'start_page': start_page,
                'end_page': end_page,
                'range_type': range_type,
                'estimated_time': len(category_names) * (end_page - (start_page or 1) + 1) * 0.5 if start_page else len(category_names) * end_page * 0.5,  # 估算时间(分钟)
                'created_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'启动爬取任务失败: {str(e)}'
        }), 500

@crawler_bp.route('/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    try:
        status = task_queue.get_task_status(task_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取任务状态失败: {str(e)}'
        }), 500

@crawler_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    try:
        success = task_queue.cancel_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '任务已取消'
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务无法取消（可能正在执行中）'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'取消任务失败: {str(e)}'
        }), 500

@crawler_bp.route('/history')
def get_crawl_history():
    """获取爬取历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        offset = (page - 1) * per_page
        history = db_manager.get_crawl_history(limit=per_page, offset=offset)
        
        # 转换数据格式
        for record in history:
            if record.get('categories') and isinstance(record['categories'], str):
                record['categories'] = json.loads(record['categories'])
        
        return jsonify({
            'success': True,
            'data': {
                'records': history,
                'page': page,
                'per_page': per_page,
                'total': len(history)  # 简化处理，实际应该查询总数
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取爬取历史失败: {str(e)}'
        }), 500

@crawler_bp.route('/debug/cookie-manager')
def debug_cookie_manager():
    """调试Cookie管理器状态"""
    return jsonify({
        'cookie_manager_exists': cookie_manager is not None,
        'cookie_manager_type': str(type(cookie_manager)),
        'has_validate_method': hasattr(cookie_manager, 'validate_cookie_format') if cookie_manager else False
    })

@crawler_bp.route('/validate-cookie', methods=['POST'])
def validate_cookie():
    """验证Cookie有效性"""
    try:
        data = request.get_json()
        cookie_string = data.get('cookie_string', '')
        
        if not cookie_string:
            return jsonify({
                'success': False,
                'error': 'Cookie不能为空'
            }), 400
        
        # 基础格式验证
        is_valid, message = cookie_manager.validate_cookie_format(cookie_string)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'valid': False,
                'message': message
            })
        
        # 检查使用限制
        cookie_hash = cookie_manager.hash_cookie(cookie_string)
        can_use_daily, daily_count = db_manager.check_cookie_limit(cookie_hash)
        can_use_time, last_time = db_manager.check_last_crawl_time(cookie_hash)
        
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Cookie格式验证通过',
            'usage_info': {
                'daily_usage': daily_count,
                'max_daily_usage': 2,
                'can_use_daily': can_use_daily,
                'can_use_time': can_use_time,
                'last_used': last_time.isoformat() if last_time else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'验证Cookie失败: {str(e)}'
        }), 500

@crawler_bp.route('/check-restrictions', methods=['POST'])
def check_crawl_restrictions():
    """检查爬取限制"""
    try:
        data = request.get_json()
        cookie_string = data.get('cookie_string', '')
        city = data.get('city', '')
        categories = data.get('categories', [])
        
        if not all([cookie_string, city, categories]):
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400
        
        restrictions = cookie_manager.check_cookie_restrictions(cookie_string, city, categories)
        
        return jsonify({
            'success': True,
            'data': restrictions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'检查限制失败: {str(e)}'
        }), 500

@crawler_bp.route('/queue-status')  
def get_queue_status():
    """获取任务队列状态"""
    try:
        status = task_queue.get_queue_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取队列状态失败: {str(e)}'
        }), 500

@crawler_bp.route('/restart-worker', methods=['POST'])
def restart_worker():
    """重启任务队列工作线程"""
    try:
        # 停止当前工作线程
        task_queue.stop_worker()
        
        # 重新启动工作线程
        task_queue.start_worker()
        
        return jsonify({
            'success': True,
            'message': '工作线程已重启',
            'worker_status': {
                'is_running': task_queue.is_running,
                'worker_alive': task_queue.worker_thread.is_alive() if task_queue.worker_thread else False
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'重启工作线程失败: {str(e)}'
        }), 500