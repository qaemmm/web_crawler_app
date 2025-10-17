"""
配置相关API端点
"""

from flask import Blueprint, jsonify, request

config_bp = Blueprint('config', __name__)

# 这些将在app.py中注入
db_manager = None
cookie_manager = None

@config_bp.route('/cities')
def get_cities():
    """获取支持的城市列表"""
    try:
        from config.crawler_config import CITIES
        
        cities_list = [{'name': name, 'code': code} for name, code in CITIES.items()]
        
        return jsonify({
            'success': True,
            'data': cities_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取城市列表失败: {str(e)}'
        }), 500

@config_bp.route('/categories/dynamic', methods=['POST'])
def discover_categories():
    """动态发现大众点评品类 - 如果失败则返回扩展静态配置"""
    try:
        data = request.get_json()
        cookie_string = data.get('cookie_string', '')
        city = data.get('city', '上海')
        
        if not cookie_string:
            return jsonify({
                'success': False,
                'data': get_static_categories(),
                'message': '未提供Cookie，返回静态品类配置',
                'is_dynamic': False
            })
        
        # 验证Cookie格式
        if not cookie_manager:
            return jsonify({
                'success': True,
                'data': get_static_categories(),
                'message': 'Cookie管理器未初始化，返回静态品类配置',
                'is_dynamic': False
            })
            
        is_valid, message = cookie_manager.validate_cookie_format(cookie_string)
        if not is_valid:
            return jsonify({
                'success': True,
                'data': get_static_categories(),
                'message': f'Cookie格式无效({message})，返回静态品类配置',
                'is_dynamic': False
            })
        
        # 尝试动态获取（简化版本，主要返回静态配置）
        try:
            # 这里可以添加真正的动态获取逻辑
            # 由于可能遇到技术问题，目前直接返回扩展的静态配置
            categories = get_static_categories()
            
            return jsonify({
                'success': True, 
                'data': categories,
                'message': f'为{city}返回扩展品类配置（共{len(categories)}个品类）',
                'is_dynamic': False,  # 标记为静态配置
                'city': city,
                'discovered_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': True,
                'data': get_static_categories(),
                'message': f'动态获取失败，返回静态配置: {str(e)}',
                'is_dynamic': False
            })
            
    except Exception as e:
        return jsonify({
            'success': True,
            'data': get_static_categories(),
            'message': f'处理请求失败，返回静态配置: {str(e)}',
            'is_dynamic': False
        })

def get_static_categories():
    """获取静态品类配置"""
    from config.crawler_config import CATEGORIES
    return [{'name': name, 'id': category_id} for name, category_id in CATEGORIES.items()]

@config_bp.route('/categories')
def get_categories():
    """获取支持的品类列表"""
    try:
        from config.crawler_config import CATEGORIES
        
        categories_list = [{'name': name, 'id': category_id} for name, category_id in CATEGORIES.items()]
        
        return jsonify({
            'success': True,
            'data': categories_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取品类列表失败: {str(e)}'
        }), 500

@config_bp.route('/crawled-combinations')
def get_crawled_combinations():
    """获取已爬取的组合（用于标记灰色）"""
    try:
        cookie_string = request.args.get('cookie_string', '')
        
        if not cookie_string:
            return jsonify({
                'success': False,
                'error': '缺少Cookie参数'
            }), 400
        
        cookie_hash = cookie_manager.hash_cookie(cookie_string)
        
        # 查询今日已爬取的组合
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT city, category FROM crawl_combinations 
                WHERE cookie_hash = ? AND crawl_date = DATE('now')
            ''', (cookie_hash,))
            
            combinations = [{'city': row[0], 'category': row[1]} for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'data': combinations
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取已爬取组合失败: {str(e)}'
        }), 500

@config_bp.route('/limits')
def get_crawl_limits():
    """获取爬取限制配置"""
    try:
        from config.crawler_config import CRAWL_LIMITS
        
        return jsonify({
            'success': True,
            'data': CRAWL_LIMITS
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取限制配置失败: {str(e)}'
        }), 500

@config_bp.route('/notices')
def get_important_notices():
    """获取重要提醒信息"""
    try:
        from config.crawler_config import IMPORTANT_NOTICES
        
        return jsonify({
            'success': True,
            'data': IMPORTANT_NOTICES
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取提醒信息失败: {str(e)}'
        }), 500

@config_bp.route('/cookies')
def get_cookies():
    """获取Cookie列表"""
    try:
        cookies = cookie_manager.list_cookies()
        
        # 隐藏敏感信息
        safe_cookies = []
        for cookie in cookies:
            safe_cookie = {
                'name': cookie['name'],
                'hash': cookie['hash'],
                'can_use': cookie['can_use'],
                'daily_usage': cookie['daily_usage'],
                'last_used': cookie['last_used'].isoformat() if cookie.get('last_used') else None,
                'status': cookie['status']
            }
            safe_cookies.append(safe_cookie)
        
        return jsonify({
            'success': True,
            'data': safe_cookies
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取Cookie列表失败: {str(e)}'
        }), 500

@config_bp.route('/cookies', methods=['POST'])
def save_cookie():
    """保存新的Cookie"""
    try:
        data = request.get_json()
        cookie_name = data.get('name', '')
        cookie_string = data.get('cookie_string', '')
        
        if not cookie_name or not cookie_string:
            return jsonify({
                'success': False,
                'error': '缺少Cookie名称或内容'
            }), 400
        
        success, message = cookie_manager.save_cookie(cookie_name, cookie_string)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'保存Cookie失败: {str(e)}'
        }), 500

@config_bp.route('/cookies/<cookie_name>', methods=['DELETE'])
def delete_cookie(cookie_name):
    """删除Cookie"""
    try:
        success, message = cookie_manager.delete_cookie(cookie_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'删除Cookie失败: {str(e)}'
        }), 500

@config_bp.route('/cookies/<cookie_name>')
def load_cookie(cookie_name):
    """加载指定的Cookie"""
    try:
        success, cookie_string, message = cookie_manager.load_cookie(cookie_name)
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'name': cookie_name,
                    'cookie_string': cookie_string
                },
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'加载Cookie失败: {str(e)}'
        }), 500