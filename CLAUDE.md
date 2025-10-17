# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a **Dianping (大众点评) Web Crawler Application** that scrapes restaurant data from Dianping.com with a Flask web interface. The application consists of:

- **Backend**: Flask API server with modular architecture
- **Frontend**: HTML/CSS/JavaScript web interface
- **Core Crawler**: Playwright-based web scraping with anti-detection measures
- **Data Processing**: CSV/Excel export with optional Gaode API integration for address enrichment

## Development Setup

### Environment Requirements
- **Operating System**: Windows 10/11 (primary target), Linux/macOS compatible
- **Python Version**: Python 3.8 or higher
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Disk Space**: At least 2GB for data storage
- **Browser**: Chromium (installed via Playwright)

### Installation Steps
```bash
# 1. Check Python version
python --version

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser
playwright install chromium

# 4. Create required directories
mkdir data\logs
mkdir data\outputs
mkdir data\temp
mkdir data\cookies
```

### Start the Application
```bash
# Start the Flask web server
python backend/app.py

# Application will be available at:
# http://127.0.0.1:5000 (localhost)
# http://0.0.0.0:5000 (network accessible)
```

### Development Tools
```bash
# Install development dependencies (optional)
pip install pytest pytest-cov black flake8 mypy

# Run linting
flake8 backend/
black backend/

# Run tests (when implemented)
pytest --cov=backend
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

## API Documentation

### Available Endpoints

#### Crawler API (`/api/crawler/*`)
- `POST /api/crawler/start` - Start a new crawl task
- `GET /api/crawler/status/{task_id}` - Get task status
- `POST /api/crawler/stop/{task_id}` - Stop a running task
- `GET /api/crawler/history` - Get crawl history
- `GET /api/crawler/stats` - Get crawling statistics

#### Configuration API (`/api/config/*`)
- `GET /api/config/cities` - Get available cities
- `GET /api/config/categories` - Get available categories
- `POST /api/config/gaode` - Configure Gaode API
- `GET /api/config/settings` - Get current settings

#### File Upload API (`/api/upload/*`)
- `POST /api/upload/csv` - Upload CSV file for processing
- `GET /api/upload/download/{filename}` - Download processed files

#### Gaode API (`/api/gaode/*`)
- `POST /api/gaode/process` - Process files with Gaode API
- `GET /api/gaode/status/{task_id}` - Check processing status

### Response Format
All APIs return JSON responses with standardized format:
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

## Security and Best Practices

### Cookie Security
- **Never share cookies**: Treat cookies as sensitive credentials
- **Cookie rotation**: Use multiple cookies to avoid rate limiting
- **Validation**: Always validate cookie format before use
- **Storage**: Store cookies securely with appropriate permissions

### Rate Limiting Compliance
- **Daily limits**: Maximum 2 tasks per cookie per day
- **Interval requirements**: Wait at least 1 hour between sessions
- **Category limits**: Maximum 2 categories per task
- **User behavior**: Simulate realistic browsing patterns

### Anti-Detection Measures
- **Random delays**: Use configurable delay ranges between requests
- **User-Agent rotation**: Rotate user agents for each session
- **Browser fingerprinting**: Implement fingerprint spoofing
- **Session isolation**: Use separate browser contexts for each cookie

## Troubleshooting

### Common Issues

#### Cookie Problems
- **Validation failure**: Ensure cookie contains required fields (`_lxsdk_cuid`, `dper`, `ll`)
- **Expired cookies**: Refresh cookies when 403 errors occur
- **Rate limiting**: Switch to different cookie if hitting limits

#### Crawler Issues
- **Captcha encounters**: Manual resolution required, system will wait for you
- **Browser crashes**: Automatic recovery mechanism in place
- **Network timeouts**: Check internet connection and retry
- **Data extraction failures**: Verify page structure hasn't changed

#### Database Problems
- **Lock issues**: Check for running processes and restart if needed
- **File permissions**: Ensure proper write permissions for data directories
- **Connection errors**: Verify database file isn't corrupted

#### Performance Issues
- **Slow crawling**: This is normal behavior to avoid detection
- **Memory usage**: Monitor system resources during long sessions
- **Disk space**: Ensure adequate space for data outputs

### Debug Mode
```bash
# Check application logs
tail -f data/logs/app.log

# Check specific crawl logs
tail -f data/logs/crawler_$(date +%Y%m%d).log
```

## Technology Stack

### Backend Technologies
- **Flask**: Web framework for REST API
- **SQLite**: Database for data persistence
- **Playwright**: Browser automation for web scraping
- **pandas**: Data processing and analysis
- **requests**: HTTP client for external APIs

### Core Dependencies
- `flask`: Web framework
- `flask-cors`: Cross-origin resource sharing
- `playwright`: Browser automation
- `fake-useragent`: User-Agent rotation
- `pandas`: Data manipulation
- `requests`: HTTP requests
- `openpyxl`: Excel file handling

### Frontend
- **HTML5/CSS3**: User interface
- **JavaScript**: Interactive features
- **Bootstrap UI**: Responsive design framework

## Important Notes

### Legal and Ethical Usage
- This crawler is designed for research and personal use only
- Respects Dianping's rate limits and anti-bot measures
- Includes captcha handling and manual intervention prompts
- Users must provide their own legitimate Dianping account cookies

### Rate Limiting and Usage Guidelines
- **Daily limits**: Maximum 2 crawl sessions per cookie per day
- **Session interval**: Minimum 1 hour between sessions
- **Category limits**: Maximum 2 categories per task, 15-30 pages each
- **User simulation**: Browse randomly before starting crawl sessions
- **Manual intervention**: Required for captcha resolution

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
- Disable debug mode in `config/crawler_config.py` (`DEBUG: False`)
- Use proper secret key for Flask sessions
- Consider adding authentication for web interface
- Monitor rate limits to avoid account blocks
- Implement proper backup strategies for database and outputs

## Vercel Deployment

### Vercel Serverless Limitations

⚠️ **Important Note**: The full crawler functionality requires Playwright browser automation, which is not supported in Vercel's serverless environment. The Vercel deployment provides a **demonstration version** with limited functionality.

### Available Features in Vercel

**✅ Available in Vercel:**
- Web interface and API documentation
- Configuration endpoints (cities, categories)
- Basic API status and health checks
- Static content serving

**❌ Not Available in Vercel:**
- Playwright web scraping functionality
- Browser automation and crawling
- File upload/download operations
- Database persistence (serverless limitations)
- Task queue and background processing

### Vercel Deployment Structure

```
web_crawler_app/
├── api/
│   ├── vercel_app.py          # Vercel-specific Flask app (simplified)
│   └── index.py               # Fallback entry point
├── vercel.json                # Vercel configuration
├── requirements.txt           # Python dependencies (reduced)
├── backend/                   # Original backend (not used in Vercel)
├── config/                    # Configuration files
└── frontend/                  # Static frontend files
```

### Vercel Configuration Files

- **vercel.json**: Routes and build configuration
- **api/vercel_app.py**: Simplified Flask application for serverless
- **requirements.txt**: Reduced dependencies (no Playwright)

### Deployment Process

```bash
# Deploy to Vercel
vercel --prod

# Or using GitHub integration
# Push to main branch triggers automatic deployment
git push origin main
```

### Local vs Vercel Deployment

| Feature | Local Deployment | Vercel Deployment |
|---------|------------------|-------------------|
| Web Scraping | ✅ Full functionality | ❌ Not supported |
| API Endpoints | ✅ Complete | ✅ Limited |
| File Operations | ✅ Full support | ❌ Serverless limits |
| Database | ✅ SQLite persistence | ❌ No persistence |
| Browser Automation | ✅ Playwright | ❌ Not supported |

### Recommended Usage

1. **Vercel Deployment**: Use for demonstration, API documentation, and testing basic functionality
2. **Local Deployment**: Use for full crawler functionality and actual data scraping
3. **Hybrid Deployment**: Combine Vercel frontend with external crawler service
4. **Cloud Browser Service**: Use third-party browser automation APIs

## Deployment Solutions for Full Functionality

### Solution 1: Hybrid Architecture (Recommended)

**Architecture**: Vercel Frontend + External Crawler Service

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Vercel App    │    │  External API    │    │  Browser/DB     │
│   (Frontend)    │◄──►│   (Crawler)      │◄──►│  (Local/Cloud)  │
│   - Web UI      │    │   - API Routes   │    │  - Playwright   │
│   - Static      │    │   - Queue Mgmt   │    │  - SQLite       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Setup Instructions**:

1. **Deploy Frontend to Vercel**:
   ```bash
   # Current repository already configured
   vercel --prod
   ```

2. **Deploy Crawler Service** (choose one):

   **Option A: VPS/Cloud Server**
   ```bash
   # On your server (Ubuntu/CentOS)
   git clone [your-repo]
   cd web_crawler_app
   pip install -r requirements.txt
   playwright install chromium
   python crawler_service/standalone_crawler.py
   ```

   **Option B: Docker Container**
   ```dockerfile
   # Dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   RUN playwright install chromium
   COPY . .
   EXPOSE 5001
   CMD ["python", "crawler_service/standalone_crawler.py"]
   ```

3. **Configure Connection**:
   - In Vercel app, set external API URL to your crawler service
   - Configure API key if needed

### Solution 2: Cloud Browser Services

**Services that work with Vercel**:
- **Browserless.io** - $49/month, 100k requests
- **ScrapingBee** - $29/month, 100k requests
- **ScrapeOps** - $29/month, 100k requests
- **Bright Data** - Enterprise solutions

**Setup**:

1. **Set Environment Variables in Vercel**:
   ```bash
   # For Browserless
   vercel env add BROWSERLESS_TOKEN

   # For ScrapingBee
   vercel env add SCRAPINGBEE_KEY

   # For ScrapeOps
   vercel env add SCRAPEOPS_KEY
   ```

2. **Access Cloud Browser API**:
   ```
   https://your-app.vercel.app/browser/
   ```

### Solution 3: Serverless Functions with Extended Limits

**Alternative Platforms**:
- **Railway** - Supports Playwright, $5/month
- **Render** - Full Docker support, $7/month
- **Heroku** - Extended execution times, $7/month
- **DigitalOcean App Platform** - $5/month

### Solution 4: Dedicated Cloud Infrastructure

**Recommended for Production**:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   App Servers    │    │   Database      │
│   (Nginx/HAProxy)│◄──►│   (Flask + Gunicorn)│◄──►│  (PostgreSQL)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Cloud Providers**:
- **AWS EC2** - $3.50/month (t3.micro)
- **Google Cloud Compute** - $4.28/month (e2-micro)
- **Azure Virtual Machine** - $3.90/month (B1s)
- **Vultr** - $3.50/month
- **Linode** - $5/month

## Cost Comparison

| Solution | Monthly Cost | Setup Complexity | Performance |
|----------|-------------|------------------|-------------|
| Vercel Only | $0 | ⭐ | ❌ No crawling |
| Hybrid (Vercel+VPS) | $5-10 | ⭐⭐ | ✅ Full features |
| Cloud Browser API | $29-49 | ⭐ | ✅ Good performance |
| Railway | $5 | ⭐ | ✅ Good performance |
| Dedicated Server | $3-10 | ⭐⭐⭐ | ✅ Best performance |

## Quick Start Deployment

### Option 1: Fastest (Hybrid with Railway)
```bash
# 1. Deploy frontend to Vercel
vercel --prod

# 2. Deploy crawler to Railway
railway login
railway init
railway up

# 3. Configure API URL in Vercel
vercel env add CRAWLER_API_URL
```

### Option 2: Most Flexible (VPS + Docker)
```bash
# 1. Deploy frontend to Vercel
vercel --prod

# 2. Setup crawler on VPS
docker build -t dianping-crawler .
docker run -p 5001:5001 dianping-crawler
```

### Option 3: Cloud Browser (Vercel Only)
```bash
# 1. Add API keys to Vercel
vercel env add BROWSERLESS_TOKEN

# 2. Deploy with browser service
vercel --prod

# 3. Access via /browser/ endpoint
```

## Monitoring and Scaling

### Health Checks
- `/api/status` - Basic service health
- `/api/crawler/stats` - Crawler performance
- `/api/system/health` - Resource usage

### Scaling Considerations
- **Horizontal scaling**: Add more crawler instances
- **Rate limiting**: Configure delays per API key
- **Load balancing**: Distribute requests across instances
- **Database**: Consider PostgreSQL for production

For production use with crawler capabilities, deploy to a traditional VPS or cloud provider that supports browser automation.