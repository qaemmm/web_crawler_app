# -*- coding: utf-8 -*-
"""
高德地图API服务模块
提供商家电话号码查询功能
"""

import requests
import pandas as pd
import time
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

# 添加项目根目录到路径
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.crawler_config import GAODE_API_CONFIG

class GaodeAPIService:
    """
    高德地图API服务类
    用于查询商家电话号码
    """
    
    def __init__(self, api_key: str = None):
        """
        初始化高德API服务
        
        Args:
            api_key: 高德API密钥，如果为空则使用配置文件中的默认值
        """
        self.api_key = api_key or GAODE_API_CONFIG.get('DEFAULT_API_KEY', '')
        self.api_url = GAODE_API_CONFIG['API_URL']
        self.timeout = GAODE_API_CONFIG['TIMEOUT']
        self.retry_count = GAODE_API_CONFIG['RETRY_COUNT']
        self.rate_limit_delay = GAODE_API_CONFIG['RATE_LIMIT_DELAY']
        self.batch_save_interval = GAODE_API_CONFIG['BATCH_SAVE_INTERVAL']
        
        self.logger = logging.getLogger(__name__)
        
        if not self.api_key:
            self.logger.warning("高德API密钥未设置，请在使用前提供有效的API密钥")
    
    def get_tel_from_gaode(self, city: str, shop_name: str) -> str:
        """
        从高德地图API获取商家电话号码
        
        Args:
            city: 城市名称
            shop_name: 商家名称
            
        Returns:
            str: 电话号码，如果未找到则返回空字符串
        """
        if not self.api_key:
            self.logger.error("API密钥未设置，无法查询电话号码")
            return ""
        
        params = {
            "key": self.api_key,
            "keywords": shop_name,
            "city": city,
            "output": "json",
            "offset": 1,
            "page": 1,
            "extensions": "all"
        }
        
        for attempt in range(self.retry_count):
            try:
                response = requests.get(
                    self.api_url, 
                    params=params, 
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get("status") == "1" and int(data.get("count", 0)) > 0:
                    pois = data.get("pois", [])
                    if pois:
                        tel = pois[0].get("tel", "")
                        # 如果tel是list，转成字符串
                        if isinstance(tel, list):
                            tel = ' / '.join(map(str, tel))
                        return str(tel)
                
                # 如果没有找到结果，记录日志但不重试
                self.logger.info(f"未找到 {city} {shop_name} 的电话信息")
                return ""
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"查询 {city} {shop_name} 时网络错误 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(1)  # 重试前等待1秒
                    continue
            except Exception as e:
                self.logger.error(f"查询 {city} {shop_name} 时出错: {e}")
                break
        
        return ""
    
    def batch_query_and_save(self, csv_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        批量查询CSV文件中商家的电话号码并保存
        
        Args:
            csv_path: 输入CSV文件路径
            output_path: 输出CSV文件路径，如果为空则在原文件名基础上添加_with_tel后缀
            
        Returns:
            Dict: 处理结果，包含成功数量、失败数量、输出文件路径等信息
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'API密钥未设置',
                'processed_count': 0,
                'success_count': 0,
                'output_file': None
            }
        
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_path)
            
            # 检查必要的列是否存在
            required_columns = ['city', 'shop_name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f'CSV文件缺少必要的列: {", ".join(missing_columns)}',
                    'processed_count': 0,
                    'success_count': 0,
                    'output_file': None
                }
            
            # 生成输出文件路径
            if not output_path:
                base_name = os.path.splitext(csv_path)[0]
                output_path = f"{base_name}_with_tel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # 初始化统计信息
            total_count = len(df)
            success_count = 0
            tel_list = []
            
            self.logger.info(f"开始批量查询电话号码，共 {total_count} 条记录")
            
            # 逐行查询电话号码
            for idx, row in df.iterrows():
                city = str(row['city'])
                shop_name = str(row['shop_name'])
                
                self.logger.info(f"正在查询 ({idx + 1}/{total_count}): {city} {shop_name}")
                
                tel = self.get_tel_from_gaode(city, shop_name)
                tel_list.append(tel)
                
                if tel:
                    success_count += 1
                    self.logger.info(f"查到电话: {tel}")
                else:
                    self.logger.info("未查到电话")
                
                # 控制API调用频率
                time.sleep(self.rate_limit_delay)
                
                # 定期保存进度
                if (idx + 1) % self.batch_save_interval == 0:
                    # 保存当前进度
                    temp_df = df.copy()
                    temp_df.loc[:idx, 'tel'] = tel_list[:idx+1]
                    try:
                        # 检查文件扩展名，决定保存格式
                        if output_path.endswith('.xlsx'):
                            temp_df.to_excel(output_path, index=False, engine='openpyxl')
                        else:
                            temp_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                    except Exception as save_error:
                        self.logger.warning(f"进度保存失败，尝试CSV格式: {save_error}")
                        # 如果保存失败，改为CSV格式
                        csv_output_path = output_path.replace('.xlsx', '.csv') if output_path.endswith('.xlsx') else output_path
                        try:
                            temp_df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
                            output_path = csv_output_path
                        except Exception as csv_error:
                            self.logger.error(f"CSV保存也失败: {csv_error}")
                    self.logger.info(f"已保存前 {idx + 1} 条记录的进度")
            
            # 最终保存所有数据
            df['tel'] = tel_list
            try:
                # 检查文件扩展名，决定保存格式
                if output_path.endswith('.xlsx'):
                    df.to_excel(output_path, index=False, engine='openpyxl')
                else:
                    df.to_csv(output_path, index=False, encoding='utf-8-sig')
            except Exception as save_error:
                self.logger.warning(f"最终保存失败，尝试CSV格式: {save_error}")
                # 如果保存失败，改为CSV格式
                csv_output_path = output_path.replace('.xlsx', '.csv') if output_path.endswith('.xlsx') else output_path
                try:
                    df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
                    output_path = csv_output_path
                except Exception as csv_error:
                    self.logger.error(f"CSV保存也失败: {csv_error}")
                    raise csv_error
            
            self.logger.info(f"批量查询完成！共处理 {total_count} 条，成功获取 {success_count} 个电话号码")
            
            return {
                'success': True,
                'processed_count': total_count,
                'success_count': success_count,
                'output_file': output_path,
                'success_rate': round(success_count / total_count * 100, 2) if total_count > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"批量查询过程中出错: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0,
                'success_count': 0,
                'output_file': None
            }
    
    def validate_api_key(self) -> Dict[str, Any]:
        """
        验证API密钥是否有效
        
        Returns:
            Dict: 验证结果
        """
        if not self.api_key:
            return {
                'valid': False,
                'error': 'API密钥为空'
            }
        
        # 使用一个简单的查询来测试API密钥
        test_result = self.get_tel_from_gaode("北京", "测试")
        
        # 如果没有抛出异常，说明API密钥基本有效
        return {
            'valid': True,
            'message': 'API密钥验证成功'
        }
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式列表
        
        Returns:
            List[str]: 支持的文件格式
        """
        return GAODE_API_CONFIG['SUPPORTED_FORMATS']
    
    def get_max_file_size(self) -> int:
        """
        获取最大文件大小限制（字节）
        
        Returns:
            int: 最大文件大小（字节）
        """
        return GAODE_API_CONFIG['MAX_FILE_SIZE_MB'] * 1024 * 1024