"""
爬虫配置文件 - 基于原版CustomCrawler的配置
"""
import os

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 城市配置 - 与原版保持一致
CITIES = {
    '长沙': 'changsha',
    '深圳': 'shenzhen',
    '苏州': 'suzhou',
    '南宁': 'nanning',
    '上海': 'shanghai',
    '广州': 'guangzhou',
    '杭州': 'hangzhou',
    '厦门': 'xiamen',
    '武汉': 'wuhan',
    '西安': 'xian',
    '北京': 'beijing'
}

# 品类配置 - 基于实际大众点评品类数据
CATEGORIES = {
    # 主要品类（显示在首页的）
    '小吃快餐': 'g112',
    '粤菜': 'g103',
    '自助餐': 'g111',
    '面包蛋糕甜品': 'g117',
    '咖啡': 'g132',
    '日式料理': 'g113',
    '火锅': 'g110',
    '西餐': 'g116',
    '小龙虾': 'g219',
    '鱼鲜海鲜': 'g251',
    '烧烤烤串': 'g508',
    '韩式料理': 'g114',
    '川菜': 'g102',
    '饮品': 'g34236',
    '粥粉面': 'g1959',
    '水果生鲜': 'g2714',
    '面馆': 'g215',
    '地方菜系': 'g34351',  # 您要测试的品类

    # 更多品类（隐藏的）
    '湘菜': 'g104',
    '特色菜': 'g34284',
    '食品滋补': 'g33759',
    '螺蛳粉': 'g32725',
    '烤肉': 'g34303',
    '私房菜': 'g1338',
    '茶餐厅': 'g207',
    '东北菜': 'g106',
    '农家菜': 'g25474',
    '北京菜': 'g311',
    '早茶': 'g34055',
    '家常菜': 'g1783',
    '东南亚菜': 'g115',
    '新疆菜': 'g3243',
    '江浙菜': 'g101',
    '素食': 'g109',
    '创意菜': 'g250',
    '中东菜': 'g234',
    '非洲菜': 'g2797',
    '其他美食': 'g118'
}

# 排序方式配置
SORT_OPTIONS = {
    'popularity': 'o2',     # 人气最多
    'reviews': 'o11',       # 评价最多
    'default': 'o2'         # 默认排序（人气最多）
}

# 爬取限制配置
CRAWL_LIMITS = {
    'MAX_CATEGORIES_PER_TASK': 2,  # 一次最多爬取2个品类
    'MAX_TASKS_PER_DAY': 2,       # 一天最多2次爬取
    'MIN_INTERVAL_HOURS': 1,      # 最小间隔1小时
    'DEFAULT_PAGES': 15,          # 默认页数
    'MAX_PAGES': 30               # 最大页数限制
}

# 反爬虫配置
ANTI_SPIDER_CONFIG = {
    'BASE_DELAY_RANGE': (20, 35),          # 基础延迟范围(秒)
    'CATEGORY_DELAY_RANGE': (60, 90),      # 品类间延迟范围(秒)
    'CAPTCHA_RETRY_MAX': 2,                # 验证码最大重试次数
    'CAPTCHA_WAIT_RANGE': (25, 40),        # 验证码等待时间范围(秒)
    'MAX_CONSECUTIVE_EMPTY': 2,            # 最大连续空页面数
    'UA_CHANGE_INTERVAL': (12, 18),        # User-Agent更换间隔页数
    'PAGE_REFRESH_PROBABILITY': 0.15,      # 页面刷新概率
    'EXTRA_INTERACTION_PROBABILITY': 0.3   # 额外交互概率
}

# Web应用配置
WEB_CONFIG = {
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'your-secret-key-here'),
    'DEBUG': os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
    'HOST': '0.0.0.0',
    'PORT': int(os.environ.get('PORT', 5000)),
    'THREADED': False  # 在Vercel serverless环境中禁用多线程
}

# 数据库配置
DATABASE_CONFIG = {
    'DB_PATH': os.path.join(BASE_DIR, 'data/database.db'),
    'BACKUP_INTERVAL_HOURS': 24,
    'MAX_HISTORY_DAYS': 30
}

# 文件路径配置
FILE_PATHS = {
    'COOKIES_DIR': os.path.join(BASE_DIR, 'data/cookies'),
    'OUTPUTS_DIR': os.path.join(BASE_DIR, 'data/outputs'),
    'LOGS_DIR': os.path.join(BASE_DIR, 'data/logs'),
    'TEMP_DIR': os.path.join(BASE_DIR, 'data/temp')
}

# 日志配置
LOGGING_CONFIG = {
    'VERSION': 1,
    'DISABLE_EXISTING_LOGGERS': False,
    'FORMATTERS': {
        'DEFAULT': {
            'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'HANDLERS': {
        'FILE': {
            'CLASS': 'logging.FileHandler',
            'LEVEL': 'INFO',
            'FORMATTER': 'DEFAULT',
            'FILENAME': 'data/logs/app.log',
            'ENCODING': 'utf-8'
        },
        'CONSOLE': {
            'CLASS': 'logging.StreamHandler',
            'LEVEL': 'INFO',
            'FORMATTER': 'DEFAULT'
        }
    },
    'LOGGERS': {
        '': {
            'HANDLERS': ['FILE', 'CONSOLE'],
            'LEVEL': 'INFO',
            'PROPAGATE': False
        }
    }
}

# 重要提醒配置
IMPORTANT_NOTICES = [
    "⚠️ 爬取数据之前一定要等待1小时",
    "🎯 随便点点页面，模拟真实用户行为", 
    "🔄 一个号一天最多爬取2次",
    "🔑 爬完后需要换号使用",
    "📊 强烈要求一个用户一次只能爬取2个品类",
    "🚫 已爬取过的城市+品类组合会被标记"
]

# UAT上传接口配置（预留）
UAT_UPLOAD_CONFIG = {
    'ENABLED': False,  # 暂时禁用，等待第三方接口
    'API_ENDPOINT': '',  # 待配置
    'API_KEY': '',       # 待配置
    'TIMEOUT': 30,       # 上传超时时间(秒)
    'RETRY_COUNT': 3     # 重试次数
}

# 高德地图API配置
GAODE_API_CONFIG = {
    'ENABLED': True,                    # 启用高德API功能
    'API_URL': 'https://restapi.amap.com/v3/place/text',
    'DEFAULT_API_KEY': '',              # 默认API Key（可为空，由用户输入）
    'TIMEOUT': 10,                      # API调用超时时间(秒)
    'RETRY_COUNT': 3,                   # 重试次数
    'RATE_LIMIT_DELAY': 0.5,           # API调用间隔(秒)，防止QPS超限
    'BATCH_SAVE_INTERVAL': 30,          # 批量保存间隔（每30条保存一次）
    'MAX_FILE_SIZE_MB': 50,             # 最大上传文件大小(MB)
    'SUPPORTED_FORMATS': ['csv'],        # 支持的文件格式
    'OUTPUT_ENCODING': 'utf-8-sig'      # 输出文件编码
}