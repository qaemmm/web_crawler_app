#!/usr/bin/env python3
"""
Web版本的CustomCrawler - 基于原版custom_crawler_for_specific_task.py
移除GUI弹窗，改为Web状态回调机制
"""

import time
import csv
import random
import re
import json
import os
import threading
from datetime import datetime
from playwright.sync_api import sync_playwright
import logging
from fake_useragent import UserAgent
from .anti_detection_config import AntiDetectionConfig

class WebCustomCrawler:
    """Web版本的定制化爬虫 - 去除GUI，添加状态回调"""
    
    def __init__(self, cookie_string, status_callback=None):
        """
        初始化Web爬虫
        Args:
            cookie_string: Cookie字符串
            status_callback: 状态回调函数，用于更新Web界面状态
        """
        self.cookie_string = cookie_string
        self.status_callback = status_callback
        
        # 统计信息
        self.captcha_count = 0
        self.skipped_pages = 0
        self.daily_request_count = 0
        self.max_daily_requests = 200
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.page_refresh_count = 0
        self.ua_change_count = 0
        
        # 初始化User-Agent生成器
        self.ua = UserAgent()
        
        # 设置详细日志
        self._setup_detailed_logging()
        
        # 城市配置
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
        
        # 品类配置（已验证的品类ID）
        self.categories = {
            '烤肉': 'g34303',
            '面包蛋糕甜品': "g117",
            '日式料理': 'g113',
            '川菜': 'g102',
            '水果生鲜': 'g2714',
            '江浙菜': 'g101',
            '小吃快餐': 'g112',
            '粤菜': 'g103',
            '火锅': 'g110',
            '烧烤烤串': 'g508',
            '小龙虾': 'g219',  # 修正ID从g1204到g219
            '咖啡': 'g132',
            '饮品': 'g34236',
            '地方菜系': 'g34351',
            # 从页面HTML中新增的品类
            '自助餐': 'g111',
            '特色菜': 'g34284',
            '食品滋补': 'g33759',
            '西餐': 'g116',
            '韩式料理': 'g114',
            '面馆': 'g215',
            '湘菜': 'g104',
            '陕菜': 'g34234',
            '鱼鲜海鲜': 'g251',
            '东北菜': 'g106',
            '新疆菜': 'g3243',
            '农家菜': 'g25474',
            '北京菜': 'g311',
            '家常菜': 'g1783',
            '私房菜': 'g1338',
            '螺蛳粉': 'g32725',
            '创意菜': 'g250',
            '东南亚菜': 'g115',
            '中东菜': 'g234',
            '非洲菜': 'g2797',
            '其他美食': 'g118'
        }
        
        # 核心字段
        self.core_fields = [
            'city',
            'primary_category',
            'secondary_category',
            'shop_name',
            'avg_price',
            'review_count',  # 新增评价数量字段
            'rating'         # 新增评分等级字段
        ]
        
        self.all_data = []

    def _setup_detailed_logging(self):
        """设置详细日志系统"""
        # 创建任务专用logger
        self.logger = logging.getLogger(f'web_crawler_{id(self)}')
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # 文件处理器
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f'crawler_{datetime.now().strftime("%Y%m%d")}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _update_status(self, message, progress=None, status_type='info', detailed=False):
        """更新状态到Web界面，同时记录详细日志"""
        # 记录详细日志
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'success': logging.INFO
        }.get(status_type, logging.INFO)
        
        self.logger.log(log_level, f"[{status_type.upper()}] {message}")
        
        # 发送到Web界面
        if self.status_callback:
            self.status_callback({
                'message': message,
                'progress': progress,
                'type': status_type,
                'timestamp': datetime.now().isoformat(),
                'stats': {
                    'captcha_count': self.captcha_count,
                    'skipped_pages': self.skipped_pages,
                    'page_refresh_count': self.page_refresh_count,
                    'ua_change_count': self.ua_change_count
                }
            })

    def get_random_user_agent(self):
        """随机生成User-Agent"""
        try:
            browsers = ['chrome', 'firefox', 'edge']
            browser = random.choice(browsers)
            
            if browser == 'chrome':
                user_agent = self.ua.chrome
            elif browser == 'firefox':
                user_agent = self.ua.firefox
            else:  # edge
                user_agent = self.ua.edge
            
            return user_agent
            
        except Exception as e:
            # 备用User-Agent列表
            fallback_uas = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ]
            return random.choice(fallback_uas)

    def get_random_viewport(self):
        """随机生成视窗大小"""
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1600, 'height': 900},
            {'width': 1280, 'height': 720}
        ]
        return random.choice(viewports)

    def get_browser_fingerprint_script(self):
        """生成简化版浏览器指纹伪装脚本 - 移除复杂功能提高稳定性"""
        language = random.choice(['zh-CN', 'en-US'])
        platform = random.choice(['Win32', 'Win64'])
        
        script = f"""
        // 基本的webdriver标识移除
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        // 删除自动化相关属性
        try {{
            if (window.cdc_adoQpoasnfa76pfcZLmcfl_Array) {{
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            }}
            if (window.cdc_adoQpoasnfa76pfcZLmcfl_Promise) {{
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            }}
            if (window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol) {{
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            }}
        }} catch (e) {{
            // 忽略错误
        }}
        
        // 基本的navigator信息 - 使用安全的方式
        try {{
            Object.defineProperty(navigator, 'language', {{
                get: () => '{language}'
            }});
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{platform}'
            }});
        }} catch (e) {{
            // 忽略错误，保持稳定性
        }}
        
        console.log('[FINGERPRINT] 简化版浏览器指纹伪装已加载');
        """
        return script

    def create_browser_context(self, playwright_instance):
        """创建带有随机指纹的浏览器上下文"""
        try:
            self.logger.info("[BROWSER] 🚀 开始创建浏览器上下文...")
            user_agent = self.get_random_user_agent()
            viewport = self.get_random_viewport()
            
            self.logger.info(f"[BROWSER] 🔧 User-Agent: {user_agent[:50]}...")
            self.logger.info(f"[BROWSER] 📐 视口大小: {viewport['width']}x{viewport['height']}")
            
            browser = playwright_instance.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-default-apps',
                    '--disable-logging',
                    '--lang=zh-CN',
                    '--accept-lang=zh-CN,zh;q=0.9,en;q=0.8',
                    f'--user-agent={user_agent}'
                ]
            )
            
            context = browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': str(random.choice([0, 1])),
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            self.logger.info("[BROWSER] ✅ 浏览器上下文创建成功")
            return browser, context
            
        except Exception as e:
            self.logger.error(f"[BROWSER] ❌ 创建浏览器上下文失败: {e}")
            self.logger.error(f"[BROWSER] 🔍 异常类型: {type(e).__name__}")
            self._update_status(f"创建浏览器上下文失败: {e}", status_type='error')
            raise

    def parse_cookies(self):
        """解析Cookie字符串（增强版设备隔离）"""
        cookies = []
        for cookie_pair in self.cookie_string.split('; '):
            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                # 过滤掉可能包含设备指纹的Cookie
                if name.strip().lower() not in ['device_id', 'fingerprint', 'client_id', 'session_id']:
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.dianping.com',
                        'path': '/'
                    })
        return cookies
    
    def clear_browser_data(self, context):
        """清理浏览器数据以避免设备关联"""
        try:
            # 清理所有存储数据
            context.clear_cookies()
            
            # 执行清理脚本
            page = context.new_page()
            page.evaluate("""
                // 清理本地存储
                if (window.localStorage) {
                    window.localStorage.clear();
                }
                
                // 清理会话存储
                if (window.sessionStorage) {
                    window.sessionStorage.clear();
                }
                
                // 清理IndexedDB
                if (window.indexedDB) {
                    window.indexedDB.databases().then(databases => {
                        databases.forEach(db => {
                            window.indexedDB.deleteDatabase(db.name);
                        });
                    }).catch(() => {});
                }
                
                // 清理缓存
                if ('caches' in window) {
                    caches.keys().then(names => {
                        names.forEach(name => {
                            caches.delete(name);
                        });
                    }).catch(() => {});
                }
            """)
            page.close()
            self.logger.info("[PRIVACY] ✅ 浏览器数据清理完成")
        except Exception as e:
            self.logger.warning(f"[PRIVACY] ⚠️ 清理浏览器数据时出现警告: {e}")

    def extract_shop_data(self, page, city_name, category_name):
        """提取商铺数据"""
        try:
            page.wait_for_load_state('networkidle', timeout=20000)
            
            if 'login' in page.url.lower():
                self._update_status("Cookie失效，被重定向到登录页面", status_type='error')
                return []
            
            content = page.content()
            shops = []

            # 使用更通用的方式匹配商铺信息块
            # 尝试多种可能的HTML结构
            shop_block_patterns = [
                r'<li class="">(.*?)</li>',  # 原始模式
                r'<li[^>]*>(.*?)</li>',      # 任何li标签
                r'<div[^>]*class="[^"]*shop-wrap[^"]*"[^>]*>(.*?)</div>',  # 商铺包装div
                r'<div[^>]*class="[^"]*shop[^"]*"[^>]*>(.*?)</div>',       # 商铺div
                r'<div[^>]*data-click-name="[^"]*shop[^"]*"[^>]*>(.*?)</div>'  # 带数据属性的div
            ]

            shop_blocks = []
            for pattern in shop_block_patterns:
                blocks = re.findall(pattern, content, re.DOTALL)
                if blocks:
                    shop_blocks = blocks
                    self.logger.info(f"[PARSE] 使用模式匹配到 {len(blocks)} 个商铺块")
                    break

            if not shop_blocks:
                self.logger.warning("[PARSE] 未找到商铺信息块，尝试从整个页面提取")
                # 如果没有找到块，尝试从整个页面内容中直接提取
                shop_blocks = [content]

            for block in shop_blocks:
                try:
                    # 商铺名称提取 - 使用多种模式
                    name_patterns = [
                        r'<h4>([^<]+)</h4>',                    # 原始模式
                        r'<h3[^>]*>([^<]+)</h3>',              # h3标签
                        r'<h2[^>]*>([^<]+)</h2>',              # h2标签
                        r'class="[^"]*shopname[^"]*"[^>]*>([^<]+)',  # 商店名称类
                        r'class="[^"]*shop-name[^"]*"[^>]*>([^<]+)', # 商店名称类变体
                        r'data-click-name="[^"]*"[^>]*>([^<]+)</a>',  # 带数据属性的链接
                    ]

                    name_match = None
                    shop_name = ""
                    for pattern in name_patterns:
                        name_match = re.search(pattern, block)
                        if name_match:
                            shop_name = name_match.group(1).strip()
                            if shop_name and len(shop_name) > 1:  # 确保商铺名称有意义
                                break

                    if not shop_name or len(shop_name) < 2:
                        continue

                    # 价格提取 - 使用更多模式
                    avg_price = ""
                    price_patterns = [
                        r'<b>￥(\d+)</b>',
                        r'￥(\d+)',
                        r'人均[：:]?\s*￥?(\d+)',
                        r'平均[：:]?\s*￥?(\d+)',
                        r'price[^>]*>￥?(\d+)',
                        r'avgprice[^>]*>￥?(\d+)'
                    ]
                    for pattern in price_patterns:
                        price_match = re.search(pattern, block)
                        if price_match:
                            avg_price = price_match.group(1)
                            break

                    # 提取评价数量 - 使用多种模式匹配
                    review_count = ""
                    review_patterns = [
                        r'<b>(\d+)</b>\s*条评价',          # 主要模式：<b>9766</b>条评价
                        r'<b>(\d+)</b>\s*条点评',          # <b>数字</b>条点评
                        r'review-num[^>]*>.*?<b>(\d+)</b>', # review-num类中的<b>标签
                        r'class="review-num"[^>]*>.*?<b>(\d+)</b>', # 完整的review-num类匹配
                        r'(\d+)\s*条评价',                 # 简单模式：数字条评价
                        r'(\d+)\s*条点评',                 # 简单模式：数字条点评
                        r'(\d+)\s*评价',                   # 数字评价
                        r'(\d+)\s*点评',                   # 数字点评
                        r'评价\s*(\d+)',                   # 评价数字
                        r'点评\s*(\d+)',                   # 点评数字
                        r'<span[^>]*>(\d+)</span>\s*条',   # span标签中的数字
                        r'>(\d+)</\w+>\s*条'               # 任何标签中的数字后跟"条"
                    ]
                    for pattern in review_patterns:
                        review_match = re.search(pattern, block, re.DOTALL)
                        if review_match:
                            review_count = review_match.group(1)
                            self.logger.debug(f"[DATA] 评价数匹配成功: {review_count} (模式: {pattern[:30]}...)")
                            break

                    # 提取评分等级 - 使用多种模式匹配星级
                    rating = ""
                    star_patterns = [
                        r'star\s+star_(\d+)\s+star_sml',       # 原始模式
                        r'class="[^"]*star[^"]*star_(\d+)[^"]*"', # CSS类中的star_数字
                        r'star_(\d+)',                          # 简单star_数字
                        r'rating-(\d+)',                        # rating-数字
                        r'score-(\d+)',                         # score-数字
                        r'class="[^"]*star[^"]*(\d{2})[^"]*"',  # 类名中的两位数字
                        r'star(\d{2})',                         # star后跟两位数字
                        r'<span[^>]*class="[^"]*star[^"]*"[^>]*>.*?(\d\.\d)</span>', # span中的小数评分
                        r'>(\d\.\d)</',                         # 任何标签中的小数评分
                        r'平均分[：:]?\s*(\d+\.?\d*)',           # 平均分文字
                        r'评分[：:]?\s*(\d+\.?\d*)',             # 评分文字
                    ]
                    for pattern in star_patterns:
                        star_match = re.search(pattern, block, re.DOTALL)
                        if star_match:
                            star_value = star_match.group(1)
                            try:
                                # 处理不同格式：45->4.5, 4->4.0, 4.5->4.5
                                if '.' in star_value:
                                    # 已经是小数格式
                                    rating = star_value
                                elif len(star_value) == 2:
                                    # 两位数字，如45->4.5
                                    rating = str(int(star_value) / 10)
                                elif len(star_value) == 1:
                                    # 一位数字，如4->4.0
                                    rating = star_value + ".0"
                                else:
                                    rating = str(float(star_value))

                                # 验证评分范围（1-5分）
                                if float(rating) > 5.0:
                                    rating = ""
                                    continue

                                self.logger.debug(f"[DATA] 评分匹配成功: {rating} (原值: {star_value}, 模式: {pattern[:30]}...)")
                            except:
                                rating = ""
                                continue
                            if rating:
                                break

                    # 调试日志 - 记录提取结果
                    if review_count or rating:
                        self.logger.info(f"[DATA] 商家: {shop_name[:10]}... 评价数: {review_count} 评分: {rating}")
                    else:
                        # 如果没有匹配到，输出部分HTML用于调试
                        debug_block = block[:500] if len(block) > 500 else block
                        self.logger.debug(f"[DATA] 商家: {shop_name[:10]}... 未找到评价数和评分")
                        self.logger.debug(f"[DEBUG] HTML片段: {debug_block[:200]}...")

                    shop = {
                        'city': city_name,
                        'primary_category': '美食',
                        'secondary_category': category_name,
                        'shop_name': shop_name,
                        'avg_price': avg_price,
                        'review_count': review_count,  # 新增评价数量
                        'rating': rating  # 新增评分等级
                    }
                    
                    shops.append(shop)
                    
                except Exception as e:
                    continue
            
            return shops
            
        except Exception as e:
            self._update_status(f"数据提取失败: {e}", status_type='error')
            return []

    def detect_captcha(self, page):
        """检测验证码"""
        try:
            captcha_selectors = [
                '.captcha',
                '#captcha',
                '[class*="verify"]',
                '[id*="verify"]',
                '.verification',
                '[class*="captcha"]'
            ]

            for selector in captcha_selectors:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    return f"检测到可见验证码元素: {selector}"

            title = page.title().lower()
            if ('验证中心' in title or 'verification center' in title or
                'captcha' in title or '人机验证' in title):
                page_content = page.content().lower()
                if ('验证码' in page_content or 'captcha' in page_content or
                    '人机验证' in page_content or 'verification' in page_content):
                    return f"页面标题和内容确认为验证页面: {title}"

            return None

        except Exception as e:
            return None

    def simulate_user_behavior(self, page):
        """用户行为模拟 - 优化版本，增加稳定性和错误处理"""
        try:
            self._update_status("开始用户行为模拟...")
            
            # 检查页面状态
            if not self._check_page_status(page):
                self.logger.warning("[BEHAVIOR] ⚠️ 页面状态异常，跳过用户行为模拟")
                return
            
            # 1. 初始等待 - 缩短时间
            initial_wait = random.uniform(1, 3)
            time.sleep(initial_wait)
            
            # 2. 简化的鼠标移动 - 减少次数和范围
            try:
                mouse_moves = random.randint(1, 3)  # 从2-8减少到1-3次
                for i in range(mouse_moves):
                    if not self._check_page_status(page):
                        break
                    
                    # 更安全的坐标范围
                    x = random.randint(400, 1000)
                    y = random.randint(200, 600)
                    
                    self._safe_mouse_move(page, x, y)
                    time.sleep(random.uniform(0.5, 1.5))  # 缩短延迟
            except Exception as e:
                self.logger.warning(f"[BEHAVIOR] 鼠标移动异常: {e}")
            
            # 3. 移除随机点击 - 这是导致问题的主要原因
            # 原来的随机点击代码被完全移除
            
            # 4. 更安全的滚动操作
            try:
                self._safe_scroll_behavior(page)
            except Exception as e:
                self.logger.warning(f"[BEHAVIOR] 滚动操作异常: {e}")
            
            # 5. 移除页面重载 - 这是导致崩溃的主要原因
            # 原来的页面重载代码被移除
            
            # 6. 最终等待 - 缩短时间
            try:
                stay_pattern = random.choice(['short', 'medium'])  # 移除long选项
                if stay_pattern == 'short':
                    final_wait = random.uniform(1, 3)  # 从2-5缩短
                else:  # medium
                    final_wait = random.uniform(2, 4)  # 从4-8缩短
                time.sleep(final_wait)
            except Exception as e:
                self.logger.warning(f"[BEHAVIOR] 最终等待异常: {e}")
            
            self.logger.info("[BEHAVIOR] ✅ 用户行为模拟完成")
            
        except Exception as e:
            self.logger.error(f"[BEHAVIOR] ❌ 用户行为模拟失败: {e}")
            time.sleep(random.uniform(2, 4))  # 缩短错误恢复时间
    
    def _check_page_status(self, page):
        """检查页面状态是否正常"""
        try:
            # 设置较短的超时时间检查页面状态
            page.evaluate("document.readyState", timeout=5000)
            return True
        except Exception:
            return False
    
    def _safe_mouse_move(self, page, x, y):
        """安全的鼠标移动操作"""
        try:
            page.mouse.move(x, y)
        except Exception as e:
            self.logger.debug(f"[BEHAVIOR] 鼠标移动失败: {e}")
    
    def _safe_scroll_behavior(self, page):
        """安全的滚动行为"""
        try:
            scroll_type = random.choice(['simple', 'reading'])  # 简化选项
            
            if scroll_type == 'simple':
                # 简单滚动 - 只滚动2-3次
                for i in range(random.randint(2, 3)):
                    if not self._check_page_status(page):
                        break
                    
                    scroll_pos = random.uniform(0.2, 0.8)
                    self._safe_evaluate(
                        page, 
                        f"window.scrollTo(0, document.body.scrollHeight * {scroll_pos})"
                    )
                    time.sleep(random.uniform(1, 2))  # 缩短延迟
            else:  # reading
                # 阅读式滚动
                positions = [0.3, 0.6]
                for pos in positions:
                    if not self._check_page_status(page):
                        break
                    
                    self._safe_evaluate(
                        page,
                        f"window.scrollTo(0, document.body.scrollHeight * {pos})"
                    )
                    time.sleep(random.uniform(1, 2))
        except Exception as e:
            self.logger.warning(f"[BEHAVIOR] 滚动行为异常: {e}")
    
    def _safe_evaluate(self, page, script, timeout=5000):
        """安全的页面脚本执行"""
        try:
            return page.evaluate(script, timeout=timeout)
        except Exception as e:
            self.logger.debug(f"[BEHAVIOR] 脚本执行失败: {e}")
            return None
    
    def _is_browser_alive(self, page):
        """检查浏览器是否还活着"""
        try:
            if page is None or page.is_closed():
                return False
            # 尝试获取页面URL，这是一个轻量级的检查
            page.url
            return True
        except Exception as e:
            self.logger.warning(f"[BROWSER] 浏览器状态检查失败: {e}")
            return False
    
    def _handle_browser_crash(self, error_msg):
        """处理浏览器崩溃"""
        self.logger.error(f"[BROWSER] ❌ 浏览器崩溃: {error_msg}")
        self.logger.info("[BROWSER] 🔄 准备重启浏览器...")
        
        # 等待一段时间再重启
        recovery_delay = random.uniform(5, 10)
        self.logger.info(f"[RECOVERY] ⏱️ 恢复延迟: {recovery_delay:.1f}秒")
        time.sleep(recovery_delay)
        
        return True  # 表示需要重新创建浏览器
    
    def _safe_delay_with_health_check(self, page, total_delay):
        """安全的分段延迟+浏览器健康检查"""
        try:
            # 将长延迟分成多个短延迟段
            segment_duration = 3  # 每段3秒
            segments = int(total_delay / segment_duration)
            remaining = total_delay % segment_duration
            
            self.logger.debug(f"[DELAY] 分段延迟: {segments}段×{segment_duration}秒 + {remaining:.1f}秒")
            
            # 执行分段延迟
            for i in range(segments):
                time.sleep(segment_duration)
                
                # 每段后检查浏览器状态
                if not self._is_browser_alive(page):
                    self.logger.error("[DELAY] ❌ 延迟期间浏览器断开")
                    raise Exception("Browser disconnected during delay")
                
                # 显示进度
                elapsed = (i + 1) * segment_duration
                self.logger.debug(f"[DELAY] 延迟进度: {elapsed:.1f}/{total_delay:.1f}秒")
            
            # 剩余时间
            if remaining > 0:
                time.sleep(remaining)
                if not self._is_browser_alive(page):
                    self.logger.error("[DELAY] ❌ 延迟期间浏览器断开")
                    raise Exception("Browser disconnected during delay")
                    
            self.logger.debug("[DELAY] ✅ 延迟完成，浏览器状态正常")
            
        except Exception as e:
            self.logger.error(f"[DELAY] ❌ 延迟期间出现异常: {e}")
            raise e
    
    def simulate_intelligent_behavior(self, page, behavior_config):
        """智能用户行为模拟 - 增加浏览器崩溃检测"""
        try:
            # 首先检查浏览器状态
            if not self._is_browser_alive(page):
                self.logger.warning("[BEHAVIOR] ⚠️ 浏览器已断开，跳过用户行为模拟")
                raise Exception("Browser disconnected")
            
            # 根据配置决定是否滚动
            if behavior_config['should_scroll']:
                try:
                    scroll_distance = random.randint(300, 800)
                    self._safe_evaluate(page, f'window.scrollBy(0, {scroll_distance})', timeout=3000)
                    scroll_delay = AntiDetectionConfig.get_random_delay('request_delay')
                    time.sleep(scroll_delay)
                    self.logger.debug("[BEHAVIOR] 📜 执行滚动行为")
                except Exception as e:
                    self.logger.warning(f"[BEHAVIOR] 滚动失败: {e}")
                
            # 移除点击操作 - 这是导致问题的主要原因之一
            # 原来的点击代码被移除
                    
            # 根据配置决定是否悬停 - 简化悬停操作
            if behavior_config.get('should_hover', False) and random.random() < 0.3:  # 降低悬停概率
                try:
                    if self._is_browser_alive(page):
                        hover_elements = page.query_selector_all('div[class*="shop"]', timeout=3000)
                        if hover_elements and len(hover_elements) > 0:
                            element = random.choice(hover_elements[:3])  # 只选择前3个元素
                            element.hover(timeout=2000)
                            hover_delay = min(AntiDetectionConfig.get_random_delay('request_delay'), 2)  # 限制最大延迟
                            time.sleep(hover_delay)
                            self.logger.debug("[BEHAVIOR] 🖱️ 执行悬停行为")
                except Exception as e:
                    self.logger.debug(f"[BEHAVIOR] 悬停失败: {e}")
                    
            # 根据配置的停留模式决定停留时间 - 缩短停留时间
            try:
                patterns = AntiDetectionConfig.get_behavior_patterns()
                stay_pattern = behavior_config['stay_pattern']
                min_time, max_time = patterns['stay_patterns'][stay_pattern]
                # 缩短停留时间到原来的一半
                stay_time = random.uniform(min_time * 0.5, max_time * 0.5)
                time.sleep(stay_time)
                self.logger.debug(f"[BEHAVIOR] ⏱️ {stay_pattern}停留: {stay_time:.1f}秒")
            except Exception as e:
                self.logger.debug(f"[BEHAVIOR] 停留时间计算失败: {e}")
                time.sleep(random.uniform(1, 3))  # 默认停留时间
            
        except Exception as e:
            self.logger.warning(f"[BEHAVIOR] ⚠️ 智能行为模拟失败: {e}")
            # 如果是浏览器断开，重新抛出异常让上层处理
            if "Browser disconnected" in str(e) or "Target page, context or browser has been closed" in str(e):
                raise e

    def crawl_specific_task(self, city_name, category_names, start_page=1, end_page=15, sort_type='popularity'):
        """
        执行特定爬取任务 - 支持页数范围和排序
        Args:
            city_name: 城市中文名称，如 '西安'
            category_names: 品类中文名称列表，如 ['咖啡', '饮品']
            start_page: 起始页数（默认1）
            end_page: 结束页数（默认15）
            sort_type: 排序方式，'popularity'(人气最多) 或 'reviews'(评价最多)
        """
        # 获取城市代码
        if city_name not in self.cities:
            self._update_status(f"不支持的城市: {city_name}", status_type='error')
            return False, []
        
        city_code = self.cities[city_name]
        
        # 获取品类ID
        category_ids = []
        for category_name in category_names:
            if category_name not in self.categories:
                self._update_status(f"不支持的品类: {category_name}", status_type='error')
                return False, []
            category_ids.append(self.categories[category_name])
        
        # 调用内部实现
        return self._crawl_specific_task_internal(city_code, city_name, category_ids, category_names, start_page, end_page, sort_type)
    
    def _crawl_specific_task_internal(self, city_code, city_name, category_ids, category_names, start_page=1, end_page=15, sort_type='popularity'):
        """
        内部爬取实现方法 - 增强版，类似重构/custom_crawler_for_specific_task.py
        Args:
            city_code: 城市代码，如 'xian'
            city_name: 城市中文名，如 '西安'
            category_ids: 品类ID列表，如 ['g132', 'g34236']
            category_names: 品类中文名列表，如 ['咖啡', '饮品']
            start_page: 起始页数
            end_page: 结束页数
            sort_type: 排序方式，'popularity'(人气最多) 或 'reviews'(评价最多)
        """
        
        self.logger.info("=" * 60)
        self.logger.info(f"[TASK] 🚀 开始爬取任务")
        self.logger.info(f"[TASK] 📍 城市: {city_name} ({city_code})")
        self.logger.info(f"[TASK] 📂 品类: {category_names} ({len(category_names)}个)")
        self.logger.info(f"[TASK] 📄 页数范围: {start_page}-{end_page}页")
        self.logger.info("=" * 60)
        
        self._update_status(f"🚀 开始爬取任务: {city_name} - {', '.join(category_names)} ({start_page}-{end_page}页)")
        
        # 重置统计变量
        self.captcha_count = 0
        self.skipped_pages = 0
        self.page_refresh_count = 0
        self.ua_change_count = 0

        if not self.cookie_string:
            self.logger.error("[TASK] ❌ Cookie为空，无法执行爬取任务")
            self._update_status("❌ Cookie为空，无法执行爬取任务", status_type='error')
            return False, []
        
        task_start_time = datetime.now()
        all_task_data = []
        
        with sync_playwright() as p:
            try:
                self.logger.info("[BROWSER] 🌐 创建浏览器上下文...")
                browser, context = self.create_browser_context(p)
                
                # 清理浏览器数据以避免设备关联
                self.clear_browser_data(context)
                
                # 移除动态指纹更换机制 - 这可能导致浏览器不稳定
                # 原来的动态指纹更换代码被移除
                
                # 随机延迟以避免时间模式关联
                initial_delay = AntiDetectionConfig.get_random_delay('initial_delay')
                self.logger.info(f"[PRIVACY] ⏱️ 初始随机延迟: {initial_delay:.1f}秒")
                time.sleep(initial_delay)
                
                cookies = self.parse_cookies()
                context.add_cookies(cookies)
                self.logger.info(f"[COOKIE] ✅ 已添加 {len(cookies)} 个Cookie")
                
                page = context.new_page()
                fingerprint_script = self.get_browser_fingerprint_script()
                page.add_init_script(fingerprint_script)
                
                total_categories = len(category_names)
                saved_files = []
                
                for i, (category_id, category_name) in enumerate(zip(category_ids, category_names)):
                    category_start_time = datetime.now()
                    category_progress = (i / total_categories) * 100
                    
                    self.logger.info("-" * 50)
                    self.logger.info(f"[CATEGORY] 📂 开始处理品类 {i+1}/{total_categories}: {category_name}")
                    self.logger.info(f"[CATEGORY] 🆔 品类ID: {category_id}")
                    self.logger.info(f"[CATEGORY] ⏱️ 开始时间: {category_start_time.strftime('%H:%M:%S')}")
                    
                    self._update_status(f"📂 开始处理品类 {i+1}/{total_categories}: {category_name}",
                                      progress=category_progress)
                     
                    category_data = []
                    consecutive_empty_pages = 0
                    page_range = end_page - start_page + 1
                    
                    # 动态设置连续无数据阈值
                    if page_range <= 5:
                        max_consecutive_empty = page_range
                    else:
                        max_consecutive_empty = max(3, page_range // 2)
                    
                    self.logger.info(f"[CATEGORY] 📊 页数范围: {start_page}-{end_page}页")
                    self.logger.info(f"[CATEGORY] ⚠️ 最大连续无数据页面: {max_consecutive_empty}")

                    # 爬取指定页数
                    for page_num in range(start_page, end_page + 1):
                        page_start_time = datetime.now()
                        
                        # 构建URL（添加排序参数）
                        sort_options = {
                            'popularity': 'o2',     # 人气最多
                            'reviews': 'o11',       # 评价最多
                            'default': 'o2'         # 默认排序（人气最多）
                        }
                        sort_suffix = sort_options.get(sort_type, sort_options['default'])

                        if page_num == 1:
                            url = f"https://www.dianping.com/{city_code}/ch10/{category_id}{sort_suffix}"
                        else:
                            url = f"https://www.dianping.com/{city_code}/ch10/{category_id}{sort_suffix}p{page_num}"
                        
                        self.logger.info(f"[PAGE] 📄 第{page_num}页: {url}")
                        self.logger.info(f"[PAGE] ⏱️ 开始时间: {page_start_time.strftime('%H:%M:%S')}")
                        
                        page_progress = category_progress + ((page_num - start_page + 1) / page_range) * (100 / total_categories)
                        self._update_status(f"📄 爬取第{page_num}页: {category_name}", progress=page_progress)
                        
                        try:
                            self.logger.info(f"[PAGE] 🔄 正在加载页面: {url}")
                            
                            # 增强页面加载稳定性
                            max_retries = 3
                            for retry in range(max_retries):
                                try:
                                    page.goto(url, timeout=30000, wait_until='domcontentloaded')
                                    
                                    # 等待页面稳定并验证加载状态
                                    page_delay = AntiDetectionConfig.get_random_delay('page_delay')
                                    time.sleep(page_delay)
                                    
                                    # 检查页面是否正确加载
                                    ready_state = page.evaluate('document.readyState')
                                    if ready_state == 'complete':
                                        self.logger.info(f"[PAGE] ✅ 页面加载成功: {url}")
                                        break
                                    else:
                                        self.logger.warning(f"[PAGE] ⚠️ 页面未完全加载，状态: {ready_state}")
                                        if retry < max_retries - 1:
                                            retry_delay = AntiDetectionConfig.get_random_delay('error_delay')
                                            time.sleep(retry_delay)
                                            continue
                                        
                                except Exception as goto_error:
                                    self.logger.warning(f"[PAGE] ⚠️ 页面加载尝试 {retry + 1}/{max_retries} 失败: {goto_error}")
                                    if retry < max_retries - 1:
                                        error_delay = AntiDetectionConfig.get_random_delay('error_delay')
                                        time.sleep(error_delay)
                                        continue
                                    else:
                                        raise goto_error
                            
                            # 额外的页面稳定性检查
                            stability_delay = AntiDetectionConfig.get_random_delay('request_delay')
                            time.sleep(stability_delay)
                            
                            # 检查验证码
                            captcha = self.detect_captcha(page)
                            if captcha:
                                self.captcha_count += 1
                                self.logger.warning(f"[CAPTCHA] 🚨 检测到验证码！第{page_num}页 - {category_name}")
                                self.logger.warning(f"[CAPTCHA] 🔍 详细信息: {captcha}")
                                
                                self._update_status(f"🚨 检测到验证码！第{page_num}页 - {category_name}", status_type='warning')
                                self._update_status("⏳ 请在浏览器中手动完成验证码验证...", status_type='warning')
                                
                                # 等待用户手动解决验证码
                                max_wait_time = 300
                                wait_interval = 10
                                waited_time = 0
                                
                                while waited_time < max_wait_time:
                                    time.sleep(wait_interval)
                                    waited_time += wait_interval
                                    
                                    current_captcha = self.detect_captcha(page)
                                    if not current_captcha:
                                        self.logger.info("[CAPTCHA] ✅ 验证码已解决")
                                        self._update_status("✅ 验证码已解决，继续爬取...", status_type='success')
                                        break
                                    else:
                                        remaining_time = max_wait_time - waited_time
                                        if remaining_time > 0:
                                            self.logger.info(f"[CAPTCHA] ⏱️ 等待中...剩余{remaining_time}秒")
                                            self._update_status(f"⏱️ 等待验证码解决中...剩余{remaining_time}秒", status_type='info')
                                
                                if waited_time >= max_wait_time:
                                    self.skipped_pages += 1
                                    self.logger.warning(f"[CAPTCHA] ⚠️ 验证码等待超时，跳过第{page_num}页")
                                    self._update_status("⚠️ 验证码等待超时，跳过当前页面", status_type='warning')
                                    continue
                                
                                # 验证码解决后重新加载
                                try:
                                    page.reload(timeout=30000)
                                    reload_delay = AntiDetectionConfig.get_random_delay('page_delay')
                                    time.sleep(reload_delay)
                                    self.logger.info("[PAGE] 🔄 页面重新加载完成")
                                except Exception as e:
                                    self.logger.error(f"[PAGE] ❌ 页面刷新失败: {e}")
                                    continue
                             
                            # 智能User-Agent轮换
                            ua_config = AntiDetectionConfig.get_user_agents()
                            if random.random() < ua_config['change_frequency']:
                                try:
                                    new_ua = self.get_random_user_agent()
                                    page.set_extra_http_headers({'User-Agent': new_ua})
                                    self.ua_change_count += 1
                                    self.logger.info(f"[UA] 🔄 第{page_num}页智能更换User-Agent")
                                except Exception as e:
                                    self.logger.warning(f"[UA] ⚠️ User-Agent更换失败: {e}")

                            # 智能用户行为模拟
                            behavior = AntiDetectionConfig.get_random_behavior()
                            self.simulate_intelligent_behavior(page, behavior)
                             
                            # 提取数据
                            page_shops = self.extract_shop_data(page, city_name, category_name)
                            page_end_time = datetime.now()
                            page_duration = (page_end_time - page_start_time).total_seconds()

                            if page_shops:
                                category_data.extend(page_shops)
                                consecutive_empty_pages = 0
                                self.logger.info(f"[PAGE] ✅ 第{page_num}页成功: {len(page_shops)} 个商铺 (耗时{page_duration:.1f}秒)")
                                self._update_status(f"✅ 第{page_num}页成功: {len(page_shops)} 个商铺")
                            else:
                                consecutive_empty_pages += 1
                                self.logger.warning(f"[PAGE] ⚠️ 第{page_num}页无数据 (耗时{page_duration:.1f}秒)")
                                self._update_status(f"⚠️ 第{page_num}页无数据", status_type='warning')

                                if consecutive_empty_pages >= max_consecutive_empty:
                                    self.logger.warning(f"[CATEGORY] ⚠️ 连续{consecutive_empty_pages}页无数据，停止爬取品类: {category_name}")
                                    self._update_status(f"⚠️ 连续{consecutive_empty_pages}页无数据，停止爬取品类: {category_name}",
                                                      status_type='warning')
                                    break
                             
                            # 页面间延迟 - 优化为分段延迟+健康检查
                            if page_num < end_page:
                                # 缩短基础延迟时间
                                base_delay = random.uniform(8, 15)  # 从20-35缩短到8-15
                                
                                if self.captcha_count > 0 and (page_num - 1) % 5 == 0:
                                    base_delay += random.uniform(5, 10)  # 从10-20缩短到5-10
                                
                                if page_num % 10 == 0:
                                    base_delay += random.uniform(8, 15)  # 从15-30缩短到8-15
                                
                                delay_pattern = random.choice(['normal', 'careful', 'relaxed'])
                                if delay_pattern == 'careful':
                                    base_delay *= random.uniform(1.1, 1.3)  # 从1.2-1.5缩小到1.1-1.3
                                elif delay_pattern == 'relaxed':
                                    base_delay *= random.uniform(0.8, 1.0)
                                
                                self.logger.info(f"[DELAY] ⏱️ 页面延迟({delay_pattern}): {base_delay:.1f}秒")
                                self._update_status(f"⏱️ 页面延迟({delay_pattern}): {base_delay:.1f}秒")
                                
                                # 分段延迟+浏览器健康检查
                                self._safe_delay_with_health_check(page, base_delay)
                             
                        except Exception as e:
                            self.logger.error(f"[PAGE] ❌ 第{page_num}页异常: {e}")
                            self.logger.error(f"[PAGE] 🔍 异常类型: {type(e).__name__}")
                            self._update_status(f"❌ 第{page_num}页异常: {e}", status_type='error')
                            
                            # 尝试页面恢复
                            try:
                                self.logger.info(f"[PAGE] 🔄 尝试恢复页面状态...")
                                page.wait_for_timeout(3000)  # 等待3秒
                                
                                # 检查页面是否还可用
                                page.evaluate('document.readyState')
                                self.logger.info(f"[PAGE] ✅ 页面状态正常，继续下一页")
                                continue
                            except Exception as recovery_error:
                                self.logger.error(f"[PAGE] ❌ 页面恢复失败: {recovery_error}")
                                self.logger.warning(f"[PAGE] ⏭️ 跳过第{page_num}页，继续下一页")
                                self._update_status(f"⏭️ 页面恢复失败，跳过第{page_num}页", status_type='warning')
                                continue
                     
                    category_end_time = datetime.now()
                    category_duration = (category_end_time - category_start_time).total_seconds()
                    
                    self.logger.info("-" * 40)
                    self.logger.info(f"[CATEGORY] ✅ 品类 {category_name} 完成")
                    self.logger.info(f"[CATEGORY] 📊 商铺数: {len(category_data)} 个")
                    self.logger.info(f"[CATEGORY] ⏱️ 耗时: {category_duration:.1f}秒")
                    
                    all_task_data.extend(category_data)
                    
                    # 每完成一个品类就保存数据（增量保存）
                    if category_data:
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                        from config.crawler_config import FILE_PATHS
                        
                        save_result = self.save_task_data(
                            category_data,
                            city_name,
                            [category_name],  # 只保存当前品类
                            FILE_PATHS['OUTPUTS_DIR'],
                            incremental=True,
                            category_name=category_name
                        )
                        if save_result:
                            saved_files.append(save_result['filename'])
                    
                    # 品类间延迟
                    if i < len(category_names) - 1:
                        delay = AntiDetectionConfig.get_random_delay('category_delay')
                        self.logger.info(f"[DELAY] ⏱️ 品类间延迟: {delay:.1f}秒")
                        self._update_status(f"⏱️ 品类间延迟: {delay:.1f}秒")
                        time.sleep(delay)
                
                # 任务完成统计
                task_end_time = datetime.now()
                task_duration = (task_end_time - task_start_time).total_seconds()
                
                self.logger.info("=" * 60)
                self.logger.info("[TASK] 🎉 任务完成!")
                self.logger.info(f"[TASK] ⏱️ 总耗时: {task_duration/60:.1f}分钟")
                self.logger.info(f"[TASK] 🏪 总商铺: {len(all_task_data)} 个")
                self.logger.info(f"[TASK] 📂 品类数: {len(category_names)} 个")
                self.logger.info("[TASK] 🛡️ 反检测统计:")
                self.logger.info(f"[TASK]   验证码遇到: {self.captcha_count} 次")
                self.logger.info(f"[TASK]   跳过页面: {self.skipped_pages} 页")
                self.logger.info(f"[TASK]   页面刷新: {self.page_refresh_count} 次")
                self.logger.info(f"[TASK]   UA更换: {self.ua_change_count} 次")
                
                if saved_files:
                    self.logger.info("[TASK] 💾 已保存文件:")
                    for file in saved_files:
                        self.logger.info(f"[TASK]   📁 {file}")
                
                self.logger.info("=" * 60)
                
                # 合并所有增量文件为最终文件
                if len(category_names) > 1 and all_task_data:
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    from config.crawler_config import FILE_PATHS
                    
                    final_save = self.save_task_data(
                        all_task_data,
                        city_name,
                        category_names,
                        FILE_PATHS['OUTPUTS_DIR']
                    )
                    if final_save:
                        saved_files.append(final_save['filename'])
                
                self._update_status(f"🎉 任务完成! 总耗时: {task_duration/60:.1f}分钟，总商铺: {len(all_task_data)} 个",
                                  progress=100, status_type='success')
                
                return True, all_task_data, saved_files
                
            except Exception as e:
                self.logger.error(f"[TASK] ❌ 任务执行异常: {e}", exc_info=True)
                self._update_status(f"❌ 任务执行异常: {e}", status_type='error')
                return False, []
            
            finally:
                # 增强的浏览器资源安全关闭逻辑
                self.logger.info("[BROWSER] 🔒 开始安全关闭浏览器资源...")
                
                # 1. 关闭页面
                try:
                    if 'page' in locals() and page and not page.is_closed():
                        self.logger.info("[BROWSER] 🔒 正在关闭页面...")
                        page.close()
                        self.logger.info("[BROWSER] ✅ 页面已关闭")
                    elif 'page' in locals() and page:
                        self.logger.info("[BROWSER] ℹ️ 页面已经关闭")
                except Exception as e:
                    self.logger.warning(f"[BROWSER] ⚠️ 页面关闭异常: {e}")
                    try:
                        # 强制关闭页面
                        if 'page' in locals() and page:
                            page._impl_obj._connection.send('Page.close', {})
                    except:
                        pass
                
                # 等待页面资源释放
                time.sleep(1)
                
                # 2. 关闭浏览器上下文
                try:
                    if 'context' in locals() and context and not context._impl_obj._is_closed_or_closing:
                        self.logger.info("[BROWSER] 🔒 正在关闭浏览器上下文...")
                        context.close()
                        self.logger.info("[BROWSER] ✅ 浏览器上下文已关闭")
                    elif 'context' in locals() and context:
                        self.logger.info("[BROWSER] ℹ️ 浏览器上下文已经关闭")
                except Exception as e:
                    self.logger.warning(f"[BROWSER] ⚠️ 浏览器上下文关闭异常: {e}")
                
                # 等待上下文资源释放
                time.sleep(1)
                
                # 3. 关闭浏览器
                try:
                    if 'browser' in locals() and browser and browser.is_connected():
                        self.logger.info("[BROWSER] 🔒 正在关闭浏览器...")
                        browser.close()
                        self.logger.info("[BROWSER] ✅ 浏览器已关闭")
                    elif 'browser' in locals() and browser:
                        self.logger.info("[BROWSER] ℹ️ 浏览器已经关闭")
                except Exception as e:
                    self.logger.warning(f"[BROWSER] ⚠️ 浏览器关闭异常: {e}")
                    try:
                        # 尝试强制终止浏览器进程
                        if 'browser' in locals() and browser:
                            browser._impl_obj._connection.send('Browser.close', {})
                    except:
                        pass
                
                # 最终等待确保所有资源完全释放
                time.sleep(2)
                self.logger.info("[BROWSER] 🔒 所有浏览器资源已安全释放")

    def save_task_data(self, data, city_name, category_names, output_dir, incremental=False, category_name=None):
        """保存任务数据到指定目录，支持增量保存"""
        if not data and not incremental:
            self.logger.warning("[SAVE] ⚠️ 没有数据需要保存")
            self._update_status("⚠️ 没有数据需要保存", status_type='warning')
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if incremental and category_name:
            # 增量保存单个品类
            filename = f'custom_crawl_{city_name}_{category_name}_partial_{timestamp}.csv'
            display_name = f"{city_name}_{category_name}_部分数据"
        else:
            # 完整保存
            categories_str = "_".join(category_names)
            filename = f'custom_crawl_{city_name}_{categories_str}_{timestamp}.csv'
            display_name = f"{city_name}_{categories_str}"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 检查文件是否存在，如果存在则追加，否则创建新文件
            file_exists = os.path.exists(filepath)
            write_header = not file_exists or not incremental
            
            with open(filepath, 'a' if incremental else 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.core_fields)
                if write_header:
                    writer.writeheader()
                for shop in data:
                    writer.writerow(shop)
            
            self.logger.info(f"[SAVE] ✅ 数据已{'追加到' if incremental else '保存到'}: {filename}")
            self._update_status(f"✅ 数据已保存: {display_name} ({len(data)}个商铺)")
            
            # 数据质量分析
            price_complete = sum(1 for shop in data if shop['avg_price'])
            price_rate = (price_complete / len(data)) * 100 if data else 0
            
            # 按品类统计
            category_stats = {}
            for shop in data:
                cat = shop['secondary_category']
                if cat not in category_stats:
                    category_stats[cat] = 0
                category_stats[cat] += 1
            
            # 记录保存信息
            self.logger.info("[SAVE] 📊 数据质量分析:")
            self.logger.info(f"[SAVE]   总商铺数: {len(data)}")
            self.logger.info(f"[SAVE]   价格完整率: {price_rate:.1f}% ({price_complete}/{len(data)})")
            self.logger.info("[SAVE]   品类分布:")
            for cat, count in category_stats.items():
                self.logger.info(f"[SAVE]     {cat}: {count} 个商铺")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'total_shops': len(data),
                'price_complete_rate': price_rate,
                'category_stats': category_stats,
                'is_incremental': incremental
            }
            
        except Exception as e:
            self.logger.error(f"[SAVE] ❌ 保存失败: {e}", exc_info=True)
            self._update_status(f"❌ 保存失败: {e}", status_type='error')
            return None