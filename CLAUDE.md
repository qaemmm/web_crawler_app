# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a **Dianping (大众点评) Web Crawler Application** that scrapes restaurant data from Dianping.com with a Flask web interface. The application consists of:

- **Backend**: Flask API server with modular architecture
- **Frontend**: HTML/CSS/JavaScript web interface
- **Core Crawler**: Playwright-based web scraping with anti-detection measures
- **Data Processing**: CSV/Excel export with optional Gaode API integration for address enrichment

## Essential Commands

### Start the Application
```bash
# Start the Flask web server
python backend/app.py

# Application will be available at:
# http://127.0.0.1:5000 (localhost)
# http://0.0.0.0:5000 (network accessible)
```

### Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Setup Required Directories
```bash
# Create data directories (if they don't exist)
mkdir data\logs
mkdir data\outputs
mkdir data\temp
mkdir data\cookies
```

## Architecture Overview

### Backend Structure
```
backend/
├── app.py              # Flask application entry point
├── api/                # API blueprints (RESTful endpoints)
│   ├── crawler_api.py  # Crawler control APIs
│   ├── config_api.py   # Configuration management
│   ├── gaode_api.py    # Gaode Maps API integration
│   ├── upload_api.py   # File upload handling
│   └── third_party_api.py # Third-party data integration
├── core/               # Core business logic
│   ├── custom_crawler.py    # Main web crawler (Playwright-based)
│   ├── task_queue.py       # Async task queue management
│   ├── category_discovery.py # Category detection logic
│   └── anti_detection_config.py # Anti-bot detection measures
└── models/             # Data models and managers
    ├── database.py     # SQLite database management
    └── cookie_manager.py # Cookie storage and validation
```

### Configuration System
- **Main config**: `config/crawler_config.py` - Contains all application settings
- **Cities**: 10 pre-configured Chinese cities (Guangzhou, Shenzhen, Shanghai, etc.)
- **Categories**: 40+ food categories with Dianping category codes
- **Anti-detection**: Configurable delays, user-agent rotation, captcha handling

### Data Flow
1. User provides Dianping cookies via web interface
2. Task queue manages crawling jobs with rate limiting
3. WebCustomCrawler uses Playwright with anti-detection measures
4. Raw data saved to CSV in `data/outputs/`
5. Optional Gaode API enrichment for detailed address/phone data
6. Database tracks tasks, statistics, and crawl history

## Key Components

### WebCustomCrawler (`backend/core/custom_crawler.py`)
- **Purpose**: Main scraping engine using Playwright
- **Anti-detection**: Random delays, user-agent rotation, captcha detection
- **Rate limiting**: Max 2 categories per task, 2 tasks per day per cookie
- **Output**: CSV files with restaurant data (name, rating, address, phone, etc.)

### TaskQueue (`backend/core/task_queue.py`)
- **Purpose**: Manages async crawling tasks
- **Features**: Task status tracking, concurrent task limitation, progress callbacks
- **Database integration**: Stores task history and statistics

### Cookie Management (`backend/models/cookie_manager.py`)
- **Purpose**: Validates and manages Dianping authentication cookies
- **Validation**: Checks cookie format and authentication status
- **Storage**: Saves cookies locally for reuse

### Database Schema (`backend/models/database.py`)
- **Tables**: tasks, crawl_data, crawl_statistics, api_configs
- **Purpose**: Tracks crawl history, statistics, and application state
- **Technology**: SQLite with automatic migrations

## Development Guidelines

### Cookie Requirements
- Cookies must be obtained from logged-in Dianping account
- Format: `_lxsdk_cuid=xxx; dper=xxx; ll=xxx; ...`
- Rate limits: 2 crawl sessions per day per cookie
- Validation happens before each crawl task

### Rate Limiting
- **Per task**: Maximum 2 categories, 15-30 pages each
- **Per day**: Maximum 2 tasks per cookie
- **Delays**: 20-35 seconds between pages, 60-90 seconds between categories
- **Captcha handling**: Automatic detection with manual resolution prompts

### File Structure
```
data/
├── outputs/       # CSV/Excel crawl results
├── logs/          # Application and crawl logs
├── temp/          # Temporary processing files
├── cookies/       # Saved cookie files
└── database.db    # SQLite database
```

### API Endpoints
- `/api/crawler/*` - Crawling control (start, stop, status)
- `/api/config/*` - Configuration management
- `/api/gaode/*` - Gaode Maps API integration
- `/api/upload/*` - File upload and processing
- `/api/third-party/*` - External data integration

### Dependencies
- **Flask + Flask-CORS**: Web server and API
- **Playwright**: Browser automation for scraping
- **pandas + openpyxl**: Data processing and Excel export
- **fake-useragent**: User-agent rotation for anti-detection
- **requests**: HTTP client for external APIs

## Important Notes

### Legal and Ethical Usage
- This crawler is designed for research and personal use only
- Respects Dianping's rate limits and anti-bot measures
- Includes captcha handling and manual intervention prompts
- Users must provide their own legitimate Dianping account cookies

### Error Handling
- Automatic captcha detection with user notification
- Graceful handling of blocked requests (403 errors)
- Task queue recovery after application restarts
- Database connection management and cleanup

### No Test Framework
- This codebase does not include automated tests
- Manual testing through the web interface is required
- Check logs at `data/logs/app.log` for debugging

### Production Considerations
- Disable debug mode in `config/crawler_config.py`
- Use proper secret key for Flask sessions
- Consider adding authentication for web interface
- Monitor rate limits to avoid account blocks