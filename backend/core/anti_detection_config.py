#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反爬虫检测配置文件
用于管理各种反爬虫策略的参数设置
"""

import random

class AntiDetectionConfig:
    """反爬虫检测配置类"""
    
    def __init__(self):
        """初始化配置"""
        pass
    
    @staticmethod
    def get_random_delays():
        """获取随机延迟配置"""
        return {
            'initial_delay': (10, 30),  # 初始启动延迟
            'page_delay': (3, 8),       # 页面间延迟
            'category_delay': (15, 45), # 品类间延迟
            'request_delay': (1, 3),    # 请求间延迟
            'error_delay': (30, 60),    # 错误后延迟
            'captcha_delay': (60, 120), # 验证码后延迟
        }
    
    @staticmethod
    def get_user_agents():
        """获取用户代理配置"""
        return {
            'change_frequency': 0.3,  # 30%概率更换UA
            'browsers': ['chrome', 'firefox', 'safari', 'edge'],
            'platforms': ['windows', 'macos', 'linux'],
            'versions': {
                'chrome': ['120.0.0.0', '119.0.0.0', '118.0.0.0'],
                'firefox': ['120.0', '119.0', '118.0'],
                'safari': ['17.1', '17.0', '16.6'],
                'edge': ['120.0.0.0', '119.0.0.0', '118.0.0.0']
            }
        }
    
    @staticmethod
    def get_viewport_configs():
        """获取视口配置"""
        return {
            'resolutions': [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1536, 'height': 864},
                {'width': 1440, 'height': 900},
                {'width': 1600, 'height': 900},
                {'width': 1280, 'height': 720},
            ],
            'change_frequency': 0.2  # 20%概率更换视口
        }
    
    @staticmethod
    def get_behavior_patterns():
        """获取行为模式配置"""
        return {
            'scroll_probability': 0.7,     # 滚动概率
            'click_probability': 0.3,      # 点击概率
            'hover_probability': 0.4,      # 悬停概率
            'back_probability': 0.1,       # 返回概率
            'refresh_probability': 0.05,   # 刷新概率
            'stay_patterns': {
                'short': (2, 5),   # 短暂停留
                'medium': (4, 8),  # 中等停留
                'long': (6, 12)    # 长时间停留
            }
        }
    
    @staticmethod
    def get_fingerprint_configs():
        """获取指纹伪装配置"""
        return {
            'screen_resolutions': [
                (1920, 1080), (1366, 768), (1536, 864),
                (1440, 900), (1600, 900), (1280, 720)
            ],
            'color_depths': [24, 32],
            'timezone_offsets': [-480, -420, -360, -300, -240],
            'languages': ['zh-CN', 'zh-TW', 'en-US', 'en-GB'],
            'platforms': ['Win32', 'Win64'],
            'hardware_concurrency': [4, 6, 8, 12, 16],
            'device_memory': [4, 8, 16, 32],
            'webgl_vendors': ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Qualcomm'],
            'webgl_renderers': [
                'Intel(R) HD Graphics',
                'NVIDIA GeForce GTX 1060',
                'AMD Radeon RX 580',
                'Intel(R) UHD Graphics 620'
            ]
        }
    
    @staticmethod
    def get_cookie_configs():
        """获取Cookie配置"""
        return {
            'filtered_names': [
                'device_id', 'fingerprint', 'client_id', 
                'session_id', 'machine_id', 'browser_id'
            ],
            'clear_frequency': 0.1,  # 10%概率清理Cookie
            'rotation_frequency': 0.2  # 20%概率轮换Cookie
        }
    
    @staticmethod
    def get_error_handling():
        """获取错误处理配置"""
        return {
            'max_retries': 3,
            'retry_delays': (5, 15),
            'captcha_max_retries': 2,
            'timeout_settings': {
                'page_load': 30000,
                'element_wait': 10000,
                'script_execution': 5000
            }
        }
    
    @staticmethod
    def get_privacy_settings():
        """获取隐私设置"""
        return {
            'clear_storage': True,
            'disable_webrtc': True,
            'disable_geolocation': True,
            'disable_notifications': True,
            'disable_camera': True,
            'disable_microphone': True,
            'spoof_timezone': True,
            'spoof_language': True
        }
    
    @classmethod
    def get_random_delay(cls, delay_type):
        """获取指定类型的随机延迟"""
        delays = cls.get_random_delays()
        if delay_type in delays:
            min_delay, max_delay = delays[delay_type]
            return random.uniform(min_delay, max_delay)
        return random.uniform(1, 3)  # 默认延迟
    
    @classmethod
    def should_change_fingerprint(cls):
        """判断是否应该更换指纹"""
        return random.random() < 0.1  # 10%概率更换指纹
    
    @classmethod
    def should_clear_data(cls):
        """判断是否应该清理数据"""
        return random.random() < 0.15  # 15%概率清理数据
    
    @classmethod
    def get_random_behavior(cls):
        """获取随机行为模式"""
        patterns = cls.get_behavior_patterns()
        return {
            'should_scroll': random.random() < patterns['scroll_probability'],
            'should_click': random.random() < patterns['click_probability'],
            'should_hover': random.random() < patterns['hover_probability'],
            'should_back': random.random() < patterns['back_probability'],
            'should_refresh': random.random() < patterns['refresh_probability'],
            'stay_pattern': random.choice(['short', 'medium', 'long'])
        }