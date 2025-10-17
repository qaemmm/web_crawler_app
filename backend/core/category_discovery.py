"""
动态品类发现模块 - 从大众点评动态获取品类信息
"""

import time
import random
import re
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

class CategoryDiscovery:
    """动态品类发现器"""
    
    def __init__(self, cookie_string):
        self.cookie_string = cookie_string
        self.ua = UserAgent()
        
        # 城市映射
        self.cities = {
            '长沙市': 'changsha',
            '深圳市': 'shenzhen', 
            '苏州市': 'suzhou',
            '南宁市': 'nanning',
            '上海市': 'shanghai',
            '广州市': 'guangzhou',
            '杭州市': 'hangzhou',
            '厦门市': 'xiamen',
            '武汉市': 'wuhan',
            '西安市': 'xian',
            '北京市':'beijing'
        }
    
    def discover_categories(self, city_name):
        """发现指定城市的品类"""
        if city_name not in self.cities:
            return self._get_fallback_categories()
            
        city_code = self.cities[city_name]
        categories = {}
        
        try:
            print(f"正在动态获取 {city_name} 的品类信息...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.ua.random,
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = context.new_page()
                
                # 设置Cookie
                cookies = self._parse_cookie_string(self.cookie_string)
                for cookie in cookies:
                    page.context.add_cookies([{
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': '.dianping.com',
                        'path': '/'
                    }])
                
                # 访问城市美食页面
                url = f"https://www.dianping.com/{city_code}/ch10"
                print(f"访问URL: {url}")
                
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待页面加载
                time.sleep(random.uniform(2, 4))
                
                # 尝试多种选择器来获取品类信息
                selectors = [
                    '.side-sub-con .sub-list a',  # 侧边栏品类链接
                    '.category-list .category-item a',  # 品类列表
                    '.nav-menu .menu-item a',  # 导航菜单
                    'a[href*="/ch10/"]'  # 包含ch10的链接
                ]
                
                for selector in selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            print(f"使用选择器 {selector} 找到 {len(elements)} 个元素")
                            for element in elements:
                                href = element.get_attribute('href')
                                text = element.text_content()
                                
                                if href and text and 'ch10' in href:
                                    # 提取品类ID
                                    match = re.search(r'/ch10/([gG]\d+)', href)
                                    if match:
                                        category_id = match.group(1)
                                        category_name = text.strip()
                                        if category_name and len(category_name) < 20:  # 过滤过长的文本
                                            categories[category_name] = category_id.lower()
                                            print(f"发现品类: {category_name} -> {category_id}")
                                            
                        if len(categories) > 10:  # 如果已经获取到足够的品类，跳出循环
                            break
                            
                    except Exception as e:
                        print(f"选择器 {selector} 执行失败: {e}")
                        continue
                
                # 如果还没有获取到品类，尝试直接从页面源码中提取
                if len(categories) < 5:
                    print("尝试从页面源码中提取品类信息...")
                    content = page.content()
                    pattern = r'href="[^"]*/([\w]+)/ch10/([gG]\d+)[^"]*"[^>]*>([^<]+)<'
                    matches = re.findall(pattern, content)
                    
                    for match in matches:
                        city_code_match, category_id, category_name = match
                        if city_code_match == city_code:
                            category_name = category_name.strip()
                            if category_name and len(category_name) < 20:
                                categories[category_name] = category_id.lower()
                                print(f"从源码发现品类: {category_name} -> {category_id}")
                
                browser.close()
                print(f"动态获取完成，共发现 {len(categories)} 个品类")
                
        except Exception as e:
            print(f"品类发现失败: {e}")
            categories = {}
        
        # 如果动态获取失败或品类数量不足，使用静态配置
        if len(categories) < 5:
            print("动态获取品类数量不足，使用静态配置")
            return self._get_fallback_categories()
        
        return categories
    
    def _get_fallback_categories(self):
        """获取静态备用品类配置"""
        return {
            # 中式料理
            '川菜': 'g102',
            '粤菜': 'g103', 
            '江浙菜': 'g101',
            '湘菜': 'g104',
            '鲁菜': 'g105',
            '东北菜': 'g106',
            '京菜': 'g108',
            '陕菜': 'g34234',
            '北京菜': 'g311',
            '家常菜': 'g1783',
            '私房菜': 'g1338',
            
            # 亚洲料理
            '日式料理': 'g113',
            '韩国料理': 'g114',
            '东南亚菜': 'g115',
            '泰式料理': 'g116',
            
            # 西式料理
            '西餐': 'g116',
            '意大利菜': 'g119',
            '法式料理': 'g120',
            '美式料理': 'g121',
            
            # 火锅烧烤
            '火锅': 'g110',
            '烧烤烤串': 'g508',
            '烤肉': 'g34303',
            '小龙虾': 'g219',
            
            # 快餐小食
            '小吃快餐': 'g112',
            '面包蛋糕甜品': 'g117',
            '咖啡': 'g132',
            '饮品': 'g34236',
            '茶餐厅': 'g207',
            '面馆': 'g215',
            '粥粉面': 'g1959',
            '早茶': 'g34055',
            '螺蛳粉': 'g32725',
            
            # 生鲜购物
            '水果生鲜': 'g2714',
            '鱼鲜海鲜': 'g251',
            
            # 特色美食
            '海鲜': 'g123',
            '素食': 'g109',
            '自助餐': 'g111',
            '创意菜': 'g250',
            '农家菜': 'g25474',
            '新疆菜': 'g3243',
            '中东菜': 'g234',
            '非洲菜': 'g2797',
            '其他美食': 'g118',
            '地方菜系': 'g34351',
            '特色菜': 'g34284'
        }
    
    def _parse_cookie_string(self, cookie_string):
        """解析Cookie字符串"""
        cookies = []
        for item in cookie_string.split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                cookies.append({'name': name, 'value': value})
        return cookies