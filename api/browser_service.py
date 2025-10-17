"""
基于云浏览器服务的爬虫API
使用Browserless、ScraperAPI等云端浏览器服务
"""

from flask import Flask, request, jsonify
import os
import sys
import json
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

app = Flask(__name__)

# 配置云浏览器服务
BROWSER_SERVICES = {
    'browserless': {
        'url': 'https://chrome.browserless.io/scrape',
        'token': os.environ.get('BROWSERLESS_TOKEN', ''),
        'enabled': bool(os.environ.get('BROWSERLESS_TOKEN'))
    },
    'scrapingbee': {
        'url': 'https://app.scrapingbee.com/api/v1/',
        'api_key': os.environ.get('SCRAPINGBEE_KEY', ''),
        'enabled': bool(os.environ.get('SCRAPINGBEE_KEY'))
    },
    'scrapeops': {
        'url': 'https://api.scrapeops.io/v1/',
        'api_key': os.environ.get('SCRAPEOPS_KEY', ''),
        'enabled': bool(os.environ.get('SCRAPEOPS_KEY'))
    }
}

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def try_cloud_browser_scrape(url, cookie_string, service_name='browserless'):
    """尝试使用云浏览器服务爬取页面"""
    service = BROWSER_SERVICES.get(service_name)
    if not service or not service['enabled']:
        raise Exception(f"Service {service_name} not configured")

    headers = {
        'Cookie': cookie_string,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    if service_name == 'browserless':
        # Browserless API
        payload = {
            'url': url,
            'elements': [
                {
                    'selector': '.shop-list .shop-item'
                }
            ],
            'waitFor': 3000,
            'headers': headers
        }
        response = requests.post(
            f"{service['url']}?token={service['token']}",
            json=payload,
            timeout=30
        )

    elif service_name == 'scrapingbee':
        # ScrapingBee API
        params = {
            'api_key': service['api_key'],
            'url': url,
            'cookies': cookie_string,
            'wait_for': '.shop-list',
            'render_js': 'true',
            'timeout': 30000
        }
        response = requests.get(service['url'], params=params, timeout=30)

    elif service_name == 'scrapeops':
        # ScrapeOps API
        params = {
            'api_key': service['api_key'],
            'url': url,
            'cookies': cookie_string,
            'render_js': 'true',
            'timeout': '30000'
        }
        response = requests.get(service['url'], params=params, timeout=30)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")

def parse_dianping_page(html_content):
    """解析大众点评页面内容"""
    soup = BeautifulSoup(html_content, 'html.parser')
    shops = []

    # 查找商家列表
    shop_items = soup.select('.shop-list .shop-item, .list-item .shop-info')

    for item in shop_items:
        try:
            shop = {
                'name': item.select_one('.shop-name, .title a').get_text(strip=True) if item.select_one('.shop-name, .title a') else '',
                'rating': item.select_one('.rating, .star-score').get_text(strip=True) if item.select_one('.rating, .star-score') else '',
                'review_count': item.select_one('.review-count, .comment-num').get_text(strip=True) if item.select_one('.review-count, .comment-num') else '',
                'price': item.select_one('.price, .avg-price').get_text(strip=True) if item.select_one('.price, .avg-price') else '',
                'address': item.select_one('.address, .location').get_text(strip=True) if item.select_one('.address, .location') else '',
                'phone': item.select_one('.phone, .tel').get_text(strip=True) if item.select_one('.phone, .tel') else '',
                'category': item.select_one('.category, .tag').get_text(strip=True) if item.select_one('.category, .tag') else ''
            }

            # 只添加非空的商家信息
            if shop['name']:
                shops.append(shop)

        except Exception as e:
            print(f"Error parsing shop item: {e}")
            continue

    return shops

@app.route('/')
def index():
    """主页"""
    return jsonify({
        'service': 'Cloud Browser Crawler Service',
        'status': 'running',
        'available_services': [name for name, config in BROWSER_SERVICES.items() if config['enabled']],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'running',
        'environment': 'cloud_browser_service',
        'timestamp': datetime.now().isoformat(),
        'services': {
            name: {
                'enabled': config['enabled'],
                'configured': bool(config.get('token') or config.get('api_key'))
            }
            for name, config in BROWSER_SERVICES.items()
        }
    })

@app.route('/api/crawler/start', methods=['POST'])
def start_crawler():
    """启动爬虫任务（使用云浏览器服务）"""
    try:
        data = request.get_json()

        # 验证参数
        required_fields = ['city', 'category', 'cookie']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # 检查可用的云服务
        available_services = [name for name, config in BROWSER_SERVICES.items() if config['enabled']]
        if not available_services:
            return jsonify({
                'success': False,
                'error': 'No cloud browser service configured. Please set BROWSERLESS_TOKEN, SCRAPINGBEE_KEY, or SCRAPEOPS_KEY environment variables.'
            }), 400

        city = data['city']
        category = data['category']
        cookie = data['cookie']
        start_page = data.get('start_page', 1)
        end_page = data.get('end_page', 3)  # 限制页数以控制API成本
        preferred_service = data.get('service', available_services[0])

        # 构造大众点评URL
        results = []
        total_pages = end_page - start_page + 1

        for page in range(start_page, end_page + 1):
            try:
                url = f"https://www.dianping.com/{city}/search/category/{category}/{page}"

                print(f"Scraping page {page}/{total_pages}: {url}")

                # 尝试使用云浏览器服务
                html_content = try_cloud_browser_scrape(url, cookie, preferred_service)

                # 解析页面内容
                shops = parse_dianping_page(html_content)

                # 添加页码信息
                for shop in shops:
                    shop['page'] = page
                    shop['city'] = city
                    shop['category'] = category
                    shop['scraped_at'] = datetime.now().isoformat()

                results.extend(shops)

                # 添加延迟以避免过于频繁的API调用
                time.sleep(2)

            except Exception as e:
                print(f"Error scraping page {page}: {e}")
                continue

        # 生成CSV文件
        if results:
            df = pd.DataFrame(results)
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')

            return jsonify({
                'success': True,
                'data': {
                    'total_shops': len(results),
                    'pages_scraped': len(set(item['page'] for item in results)),
                    'csv_content': csv_content,
                    'city': city,
                    'category': category,
                    'service_used': preferred_service
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No data found. Please check your cookie, URL, or service configuration.'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-services')
def test_services():
    """测试云服务配置"""
    test_results = {}

    for name, config in BROWSER_SERVICES.items():
        if config['enabled']:
            try:
                # 测试简单的请求
                if name == 'browserless':
                    response = requests.get(f"https://chrome.browserless.io/status?token={config['token']}", timeout=10)
                    test_results[name] = {
                        'status': 'success' if response.status_code == 200 else 'failed',
                        'response': response.status_code
                    }
                else:
                    # 对于其他服务，只检查密钥是否存在
                    test_results[name] = {
                        'status': 'configured',
                        'message': 'API key is set'
                    }
            except Exception as e:
                test_results[name] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results[name] = {
                'status': 'not_configured',
                'message': 'API key or token not set'
            }

    return jsonify({
        'success': True,
        'services': test_results
    })

if __name__ == '__main__':
    print("Starting Cloud Browser Crawler Service...")
    print("Available services:")
    for name, config in BROWSER_SERVICES.items():
        status = "✅ Configured" if config['enabled'] else "❌ Not configured"
        print(f"  {name}: {status}")

    if not any(config['enabled'] for config in BROWSER_SERVICES.values()):
        print("\n⚠️  Warning: No cloud browser service configured!")
        print("Please set one of the following environment variables:")
        print("  - BROWSERLESS_TOKEN")
        print("  - SCRAPINGBEE_KEY")
        print("  - SCRAPEOPS_KEY")

    app.run(host='0.0.0.0', port=5002, debug=False)