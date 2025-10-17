# -*- coding: utf-8 -*-
"""
第三方API集成模块
提供文件上传、数据导入和token验证的测试接口
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
import requests
from werkzeug.utils import secure_filename

# 创建蓝图
third_party_bp = Blueprint('third_party', __name__)
logger = logging.getLogger(__name__)

# 第三方API配置
THIRD_PARTY_CONFIG = {
    'test': {
        'base_url': 'http://47.112.30.182:22402',
        'upload_endpoint': '/api/opt-file/file/upl',
        'import_endpoint': '/api/opt-commerce/ai/brand/importByFileIds',
        'task_status_endpoint': '/api/ai/brand/task/status'
    },
    'production': {
        'base_url': 'https://erqi.leyingiot.com',
        'upload_endpoint': '/api/opt-file/file/upl',
        'import_endpoint': '/api/opt-commerce/ai/brand/importByFileIds',
        'task_status_endpoint': '/api/ai/brand/task/status'
    }
}

def get_config(environment='production'):
    """获取指定环境的配置"""
    return THIRD_PARTY_CONFIG.get(environment, THIRD_PARTY_CONFIG['production'])

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@third_party_bp.route('/production/upload', methods=['POST'])
def production_upload():
    """生产环境文件上传接口"""
    return upload_file('production')

@third_party_bp.route('/test/upload', methods=['POST'])
def test_upload():
    """测试环境文件上传接口"""
    return upload_file('test')

def upload_file(environment):
    """统一的文件上传函数"""
    try:
        logger.info(f"Received headers: {request.headers}")
        # 统一token获取：优先token头，其次Authorization Bearer
        token = request.headers.get('token')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                logger.warning("Missing token in header")
                return jsonify({
                    'success': False,
                    'message': '需要提供有效的token'
                }), 401
        logger.info(f"Extracted token: {token[:10]}... (length: {len(token)})")
        
        # 检查文件
        if 'file' not in request.files:
            logger.warning("No file in request")
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400
        
        file = request.files['file']
        logger.info(f"Uploading file: {file.filename}")
        
        # 获取环境配置
        config = get_config(environment)
        
        # 调用实际的第三方API
        # 重新构造FormData，确保包含busSubType参数
        files = {
            'file': (file.filename, file.stream, file.content_type),
            'busSubType': (None, '1001')
        }
        headers = {'token': token}
        logger.info(f"准备上传文件到第三方API: {file.filename}, 大小: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
        logger.info(f"上传参数: busSubType=1001")
        logger.info(f"请求头: {headers}")
        logger.info(f"目标URL: {config['base_url']}{config['upload_endpoint']}")
        
        response = requests.post(
            f"{config['base_url']}{config['upload_endpoint']}",
            files=files,
            headers=headers,
            timeout=30
        )
        logger.info(f"第三方API上传响应状态: {response.status_code}")
        logger.info(f"第三方API上传响应内容: {response.text}")
        
        # 解析响应并记录详细信息
        try:
            response_data = response.json()
            logger.info(f"解析后的响应数据: {response_data}")
            if response_data.get('code') == 0 and response_data.get('data', {}).get('fileId'):
                logger.info(f"文件上传成功，获得fileId: {response_data['data']['fileId']}")
            else:
                logger.warning(f"文件上传可能失败，响应码: {response_data.get('code')}, 消息: {response_data.get('msg')}")
        except Exception as e:
            logger.error(f"解析上传响应失败: {e}")
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'message': f'第三方API调用失败: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        logger.error(f"第三方API调用异常: {e}")
        return jsonify({
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"生产环境文件上传失败: {e}")
        return jsonify({
            'success': False,
            'message': f'上传失败: {str(e)}'
        }), 500

@third_party_bp.route('/production/import', methods=['POST'])
def production_import():
    """生产环境数据导入接口"""
    return import_data('production')

@third_party_bp.route('/test/import', methods=['POST'])
def test_import():
    """测试环境数据导入接口"""
    return import_data('test')

def import_data(environment):
    """统一的数据导入函数"""
    try:
        logger.info(f"Received headers: {request.headers}")
        # 验证token - 支持token:xxx格式
        token = request.headers.get('token')
        if not token:
            # 兼容旧版Authorization Bearer格式
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                logger.warning("Missing token in header")
                return jsonify({
                    'success': False,
                    'message': '需要提供有效的token'
                }), 401
        logger.info(f"Extracted token: {token[:10]}... (length: {len(token)})")
        data = request.get_json()
        logger.info(f"接收到导入请求数据: {data}")
        
        # 验证fileIds参数
        file_ids = data.get('fileIds', [])
        if not file_ids:
            logger.error("导入请求缺少fileIds参数")
            return jsonify({
                'success': False,
                'message': '缺少fileIds参数'
            }), 400
        
        logger.info(f"准备导入文件，fileIds: {file_ids}, testMode: {data.get('testMode', False)}")
        
        # 获取环境配置
        config = get_config(environment)
        
        # 调用实际的第三方API
        headers = {
            'token': token,
            'Content-Type': 'application/json'
        }
        logger.info(f"导入请求头: {headers}")
        logger.info(f"目标导入URL: {config['base_url']}{config['import_endpoint']}")
        logger.info(f"发送导入请求体: {data}")
        
        response = requests.post(
            f"{config['base_url']}{config['import_endpoint']}",
            json=data,
            headers=headers,
            timeout=30
        )
        logger.info(f"第三方API导入响应状态: {response.status_code}")
        logger.info(f"第三方API导入响应内容: {response.text}")
        
        # 解析导入响应并记录详细信息
        try:
            response_data = response.json()
            logger.info(f"解析后的导入响应数据: {response_data}")
            if response_data.get('code') == 0:
                task_id = response_data.get('data')
                logger.info(f"数据导入任务启动成功，任务ID: {task_id}")
            else:
                logger.warning(f"数据导入可能失败，响应码: {response_data.get('code')}, 消息: {response_data.get('msg')}")
        except Exception as e:
            logger.error(f"解析导入响应失败: {e}")
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'message': f'第三方API调用失败: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        logger.error(f"第三方API调用异常: {e}")
        return jsonify({
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"生产环境数据导入失败: {e}")
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

@third_party_bp.route('/production/task/status', methods=['GET'])
def production_task_status():
    """生产环境任务状态查询接口"""
    return task_status('production')

@third_party_bp.route('/test/task/status', methods=['GET'])
def test_task_status():
    """测试环境任务状态查询接口"""
    return task_status('test')

def task_status(environment):
    """统一的任务状态查询函数"""
    try:
        logger.info(f"Received headers: {request.headers}")
        # 验证token - 支持token:xxx格式
        token = request.headers.get('token')
        if not token:
            # 兼容旧版Authorization Bearer格式
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                logger.warning("Missing token in header")
                return jsonify({
                    'success': False,
                    'message': '需要提供有效的token'
                }), 401
        logger.info(f"Extracted token: {token[:10]}... (length: {len(token)})")
        
        # 获取任务ID
        task_id = request.args.get('taskId')
        if not task_id:
            logger.error("任务状态查询缺少taskId参数")
            return jsonify({
                'success': False,
                'message': '缺少taskId参数'
            }), 400
        
        logger.info(f"查询任务状态，任务ID: {task_id}")
        
        # 获取环境配置
        config = get_config(environment)
        
        # 调用实际的第三方API
        headers = {
            'token': token,
            'Content-Type': 'application/json'
        }
        logger.info(f"任务状态查询请求头: {headers}")
        logger.info(f"目标查询URL: {config['base_url']}{config['task_status_endpoint']}?taskId={task_id}")
        
        response = requests.get(
            f"{config['base_url']}{config['task_status_endpoint']}?taskId={task_id}",
            headers=headers,
            timeout=30
        )
        logger.info(f"第三方API任务状态查询响应状态: {response.status_code}")
        logger.info(f"第三方API任务状态查询响应内容: {response.text}")
        
        # 解析响应并记录详细信息
        try:
            response_data = response.json()
            logger.info(f"解析后的任务状态响应数据: {response_data}")
            if response_data.get('code') == 0:
                task_data = response_data.get('data', {})
                logger.info(f"任务状态查询成功，状态: {task_data.get('status')}, 进度: {task_data.get('progress', 0)}%")
            else:
                logger.warning(f"任务状态查询可能失败，响应码: {response_data.get('code')}, 消息: {response_data.get('msg')}")
        except Exception as e:
            logger.error(f"解析任务状态响应失败: {e}")
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'message': f'第三方API调用失败: {response.status_code}',
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        logger.error(f"第三方API调用异常: {e}")
        return jsonify({
            'success': False,
            'message': f'网络请求失败: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"生产环境任务状态查询失败: {e}")
        return jsonify({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }), 500