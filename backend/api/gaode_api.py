# -*- coding: utf-8 -*-
"""
高德地图API接口模块
提供文件上传和电话号码查询功能
"""

import os
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import tempfile

# 添加项目根目录到路径
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.crawler_config import GAODE_API_CONFIG, FILE_PATHS
from backend.core.gaode_service import GaodeAPIService

# 创建蓝图
gaode_bp = Blueprint('gaode', __name__, url_prefix='/api/gaode')
logger = logging.getLogger(__name__)

@gaode_bp.route('/validate_key', methods=['POST'])
def validate_api_key():
    """
    验证高德API密钥是否有效
    """
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API密钥不能为空'
            }), 400
        
        # 创建服务实例并验证
        gaode_service = GaodeAPIService(api_key)
        result = gaode_service.validate_api_key()
        
        return jsonify({
            'success': result['valid'],
            'message': result.get('message', result.get('error', ''))
        })
        
    except Exception as e:
        logger.error(f"验证API密钥时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'验证过程中出错: {str(e)}'
        }), 500

@gaode_bp.route('/upload_and_query', methods=['POST'])
def upload_and_query():
    """
    上传CSV文件并查询电话号码
    """
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API密钥不能为空'
            }), 400
        
        # 检查文件格式
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.csv'):
            return jsonify({
                'success': False,
                'error': '只支持CSV格式文件'
            }), 400
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        max_size = GAODE_API_CONFIG['MAX_FILE_SIZE_MB'] * 1024 * 1024
        if file_size > max_size:
            return jsonify({
                'success': False,
                'error': f'文件大小超过限制（最大{GAODE_API_CONFIG["MAX_FILE_SIZE_MB"]}MB）'
            }), 400
        
        # 保存上传的文件到临时目录
        temp_dir = FILE_PATHS['TEMP_DIR']
        os.makedirs(temp_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"upload_{timestamp}_{filename}"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        file.save(temp_filepath)
        logger.info(f"文件已保存到临时目录: {temp_filepath}")
        
        # 创建高德服务实例并处理文件
        gaode_service = GaodeAPIService(api_key)
        
        # 生成输出文件路径
        output_dir = FILE_PATHS['OUTPUTS_DIR']
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_with_tel_{timestamp}.csv"
        output_filepath = os.path.join(output_dir, output_filename)
        
        # 执行批量查询
        result = gaode_service.batch_query_and_save(temp_filepath, output_filepath)
        
        # 清理临时文件
        try:
            os.remove(temp_filepath)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f"处理完成！共处理 {result['processed_count']} 条记录，成功获取 {result['success_count']} 个电话号码",
                'processed_count': result['processed_count'],
                'success_count': result['success_count'],
                'success_rate': result['success_rate'],
                'output_filename': output_filename,
                'download_url': f'/api/gaode/download/{output_filename}'
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"处理文件上传和查询时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'处理过程中出错: {str(e)}'
        }), 500

@gaode_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    下载处理后的文件
    """
    try:
        # 安全检查文件名
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({
                'success': False,
                'error': '无效的文件名'
            }), 400
        
        file_path = os.path.join(FILE_PATHS['OUTPUTS_DIR'], safe_filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"下载文件时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'下载过程中出错: {str(e)}'
        }), 500

@gaode_bp.route('/config', methods=['GET'])
def get_config():
    """
    获取高德API相关配置信息
    """
    try:
        return jsonify({
            'success': True,
            'config': {
                'enabled': GAODE_API_CONFIG['ENABLED'],
                'max_file_size_mb': GAODE_API_CONFIG['MAX_FILE_SIZE_MB'],
                'supported_formats': GAODE_API_CONFIG['SUPPORTED_FORMATS'],
                'rate_limit_delay': GAODE_API_CONFIG['RATE_LIMIT_DELAY'],
                'batch_save_interval': GAODE_API_CONFIG['BATCH_SAVE_INTERVAL']
            }
        })
        
    except Exception as e:
        logger.error(f"获取配置信息时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'获取配置时出错: {str(e)}'
        }), 500

@gaode_bp.route('/test_query', methods=['POST'])
def test_query():
    """
    测试单个商家的电话查询
    """
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        city = data.get('city', '').strip()
        shop_name = data.get('shop_name', '').strip()
        
        if not all([api_key, city, shop_name]):
            return jsonify({
                'success': False,
                'error': 'API密钥、城市和商家名称都不能为空'
            }), 400
        
        # 创建服务实例并查询
        gaode_service = GaodeAPIService(api_key)
        tel = gaode_service.get_tel_from_gaode(city, shop_name)
        
        return jsonify({
            'success': True,
            'city': city,
            'shop_name': shop_name,
            'tel': tel,
            'found': bool(tel)
        })
        
    except Exception as e:
        logger.error(f"测试查询时出错: {e}")
        return jsonify({
            'success': False,
            'error': f'查询过程中出错: {str(e)}'
        }), 500