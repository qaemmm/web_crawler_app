"""
文件上传API端点 - 预留UAT上传接口
"""

from flask import Blueprint, jsonify, request, send_from_directory
import os
from datetime import datetime

upload_bp = Blueprint('upload', __name__)

# 这些将在app.py中注入
db_manager = None

@upload_bp.route('/to-uat', methods=['POST'])
def upload_to_uat():
    """上传文件到UAT环境 - 预留接口"""
    try:
        data = request.get_json()
        file_path = data.get('file_path', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': '缺少文件路径参数'
            }), 400
        
        # 检查文件是否存在
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.crawler_config import FILE_PATHS
        full_path = os.path.join(FILE_PATHS['OUTPUTS_DIR'], file_path)
        
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # TODO: 这里是预留的UAT上传接口
        # 当你有第三方平台接口时，在这里调用
        
        # 目前返回预留提示
        return jsonify({
            'success': False,
            'error': 'UAT上传功能暂未实现',
            'message': '这是预留的接口，等待第三方平台对接',
            'file_info': {
                'file_path': file_path,
                'file_size': os.path.getsize(full_path),
                'file_exists': True
            }
        }), 501  # 501 Not Implemented
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'上传失败: {str(e)}'
        }), 500

@upload_bp.route('/status/<upload_id>')
def get_upload_status(upload_id):
    """获取上传状态 - 预留接口"""
    try:
        # TODO: 这里是预留的上传状态查询接口
        
        return jsonify({
            'success': False,
            'error': '上传状态查询功能暂未实现',
            'message': '这是预留的接口，等待第三方平台对接'
        }), 501
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'查询上传状态失败: {str(e)}'
        }), 500

@upload_bp.route('/files')
def list_output_files():
    """列出可上传的输出文件"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.crawler_config import FILE_PATHS
        
        files = []
        output_dir = FILE_PATHS['OUTPUTS_DIR']
        
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(output_dir, filename)
                    stat = os.stat(file_path)
                    
                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # 按修改时间倒序排列
        files.sort(key=lambda x: x['modified_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': files
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取文件列表失败: {str(e)}'
        }), 500

@upload_bp.route('/download/<filename>')
def download_file(filename):
    """下载输出文件"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.crawler_config import FILE_PATHS
        
        return send_from_directory(
            FILE_PATHS['OUTPUTS_DIR'], 
            filename, 
            as_attachment=True
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'下载文件失败: {str(e)}'
        }), 500

@upload_bp.route('/preview/<filename>')
def preview_file(filename):
    """预览CSV文件内容"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.crawler_config import FILE_PATHS
        import csv
        
        file_path = os.path.join(FILE_PATHS['OUTPUTS_DIR'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 读取CSV文件前几行进行预览
        preview_data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            for i, row in enumerate(reader):
                if i >= 10:  # 只预览前10行
                    break
                preview_data.append(dict(row))
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'headers': headers,
                'preview_rows': preview_data,
                'total_preview_rows': len(preview_data)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'预览文件失败: {str(e)}'
        }), 500

# UAT配置接口 - 用于将来配置第三方平台信息
@upload_bp.route('/uat-config', methods=['GET', 'POST'])
def uat_config():
    """UAT上传配置 - 预留接口"""
    if request.method == 'GET':
        # 获取当前UAT配置
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config.crawler_config import UAT_UPLOAD_CONFIG
        
        # 隐藏敏感信息
        safe_config = {
            'enabled': UAT_UPLOAD_CONFIG['ENABLED'],
            'has_endpoint': bool(UAT_UPLOAD_CONFIG['API_ENDPOINT']),
            'has_api_key': bool(UAT_UPLOAD_CONFIG['API_KEY']),
            'timeout': UAT_UPLOAD_CONFIG['TIMEOUT'],
            'retry_count': UAT_UPLOAD_CONFIG['RETRY_COUNT']
        }
        
        return jsonify({
            'success': True,
            'data': safe_config
        })
        
    elif request.method == 'POST':
        # 更新UAT配置 - 预留功能
        return jsonify({
            'success': False,
            'error': 'UAT配置更新功能暂未实现',
            'message': '等待第三方平台对接后实现'
        }), 501