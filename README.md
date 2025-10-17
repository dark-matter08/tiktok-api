# TikTok API Backend

A production-ready FastAPI backend that provides a comprehensive REST API for TikTok data using the [TikTok-Api](https://github.com/davidteather/TikTok-Api) Python wrapper.

## Features

- **Full TikTok API Coverage**: Trending videos, user info, video details, hashtags, search, and sounds
- **API Key Authentication**: Secure access control with configurable API keys
- **Rate Limiting**: Per-endpoint rate limiting with Redis backend
- **MS Token Rotation**: Automatic token rotation and health monitoring
- **Production Ready**: Docker support, health checks, and comprehensive error handling
- **Interactive Documentation**: Auto-generated Swagger/OpenAPI documentation
- **Poetry Package Management**: Modern Python dependency management

## Quick Start

### Prerequisites

- Python 3.9+
- Poetry
- Redis (for rate limiting)
- MS Tokens from TikTok (see [How to Get MS Tokens](#how-to-get-ms-tokens))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tik-tok-api
   ```

2. **Install dependencies with Poetry**
   ```bash
   poetry install
   ```

3. **Install Playwright browsers**
   ```bash
   poetry run playwright install
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## Docker Deployment

### Development

```bash
# Start Redis and the API
docker-compose up

# Or run in background
docker-compose up -d
```

### Production

```bash
# Start with Nginx reverse proxy
docker-compose --profile production up -d
```

## Features

### Video URL Parsing

The API supports extracting video IDs from TikTok URLs in multiple formats:

- **Standard URLs**: `https://www.tiktok.com/@username/video/1234567890123456789`
- **Short URLs**: `https://vm.tiktok.com/ZMxxx/`
- **Alternative short**: `https://www.tiktok.com/t/ZMxxx/`

You can use TikTok URLs in two ways:

1. **Direct URL usage**: Pass the URL directly to the `/api/v1/video/{video_id}` endpoint (URL-encoded)
2. **URL parsing endpoint**: Use `/api/v1/video/parse-url` to extract just the video ID

The API automatically resolves shortened URLs to extract the video ID.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEYS` | Comma-separated list of valid API keys | `default-api-key` |
| `MS_TOKENS` | Comma-separated list of MS tokens | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `RATE_LIMIT_PER_MINUTE` | Global rate limit per minute | `100` |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `TIKTOK_BROWSER` | Browser for TikTok API (chromium/firefox/webkit) | `chromium` |
| `TIKTOK_SLEEP_AFTER` | Sleep time after creating sessions | `3` |
| `TIKTOK_NUM_SESSIONS` | Number of TikTok sessions | `1` |
| `TIKTOK_HEADLESS` | Run TikTok browser in headless mode | `true` |
| `ENABLE_PROXY` | Enable proxy rotation via Webshare | `false` |
| `WEBSHARE_API_KEY` | Webshare API key for proxy service | None |
| `PROXY_ALGORITHM` | Proxy rotation algorithm (round-robin/random/first) | `round-robin` |
| `WEBSHARE_COOKIE` | Webshare cookie for API authentication | `_tid=53ee2bfc-4e7f-4752-a718-e72fd5db7e3c` |

### How to Get MS Tokens

1. Open TikTok.com in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies
4. Find the `ms_token` cookie value
5. Copy the value and add it to your `MS_TOKENS` environment variable

**Note**: You can have multiple MS tokens for better reliability and rate limit distribution.

### Proxy Configuration

This API supports proxy rotation using Webshare via the `proxyproviders` package to avoid IP-based rate limits and bypass geo-restrictions.

#### Setup

1. Get a Webshare API key from [https://www.webshare.io](https://www.webshare.io)
2. Configure environment variables:

```env
ENABLE_PROXY=true
WEBSHARE_API_KEY=your_api_key_here
PROXY_ALGORITHM=round-robin  # Options: round-robin, random, first
WEBSHARE_COOKIE=_tid=53ee2bfc-4e7f-4752-a718-e72fd5db7e3c
```

#### Proxy Algorithms

- **round-robin**: Cycles through proxies sequentially (default)
- **random**: Selects a random proxy for each request
- **first**: Always uses the first available proxy

#### Monitoring

Check proxy status:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/proxy/status
```

#### Benefits

- Avoid IP-based rate limits
- Bypass geo-restrictions
- Improved reliability with automatic failover
- Smart proxy rotation managed by proxyproviders package

## API Endpoints

### Authentication

All endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/trending/videos
```

### Trending Videos

```bash
GET /api/v1/trending/videos?count=30
```

### User Information

```bash
# Get user info
GET /api/v1/user/{username}/info

# Get user videos
GET /api/v1/user/{username}/videos?count=30

# Get user followers
GET /api/v1/user/{username}/followers?count=30

# Get user following
GET /api/v1/user/{username}/following?count=30
```

### Video Information

```bash
# Get video details (accepts video ID or URL)
GET /api/v1/video/{video_id}

# Example with video ID
GET /api/v1/video/7123456789012345678

# Example with TikTok URL (URL-encoded)
GET /api/v1/video/https%3A%2F%2Fwww.tiktok.com%2F%40username%2Fvideo%2F7123456789012345678

# Parse video URL to get ID
POST /api/v1/video/parse-url
Content-Type: application/json

{
  "url": "https://www.tiktok.com/@username/video/7123456789012345678",
  "resolve_redirects": true
}

# Get video comments
GET /api/v1/video/{video_id}/comments?count=30
```

### Hashtag Information

```bash
# Get hashtag videos
GET /api/v1/hashtag/{hashtag}/videos?count=30

# Get hashtag info
GET /api/v1/hashtag/{hashtag}/info
```

### Search

```bash
# Search users
GET /api/v1/search/users?q=query&count=30

# Search videos
GET /api/v1/search/videos?q=query&count=30
```

### Sound Information

```bash
# Get sound videos
GET /api/v1/sound/{sound_id}/videos?count=30

# Get sound info
GET /api/v1/sound/{sound_id}/info
```

### Health & Monitoring

```bash
# Health check
GET /health

# Token statistics
GET /token-stats
```

## Rate Limiting

The API implements per-endpoint rate limiting:

- **Trending**: 200 requests/minute
- **User**: 100 requests/minute
- **Video**: 150 requests/minute
- **Hashtag**: 100 requests/minute
- **Search**: 50 requests/minute
- **Sound**: 100 requests/minute
- **Health**: 1000 requests/minute

Rate limits are tracked per API key and stored in Redis.

## Error Handling

The API returns structured error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "status_code": 400
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized (missing API key)
- `403`: Forbidden (invalid API key)
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limit Exceeded
- `500`: Internal Server Error

## Development

### Project Structure

```
tik-tok-api/
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── models/               # Pydantic models
│   ├── services/             # Business logic
│   ├── middleware/           # Custom middleware
│   ├── config.py             # Configuration
│   ├── dependencies.py       # Auth & rate limiting
│   └── main.py               # FastAPI app
├── tests/                    # Test files
├── docker-compose.yml        # Docker setup
├── Dockerfile               # Docker image
└── pyproject.toml           # Poetry configuration
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black app/
poetry run ruff check app/
```

### Adding New Endpoints

1. Create endpoint file in `app/api/v1/endpoints/`
2. Add Pydantic models in `app/models/schemas.py`
3. Add service methods in `app/services/tiktok_service.py`
4. Include router in `app/api/v1/router.py`

## Production Considerations

### Security

- Use strong API keys
- Enable HTTPS in production
- Configure proper CORS settings
- Use environment variables for secrets
- Regularly rotate MS tokens

### Monitoring

- Monitor `/health` endpoint
- Check `/token-stats` for token health
- Set up logging aggregation
- Monitor rate limiting metrics

### Scaling

- Use multiple MS tokens for better reliability
- Consider horizontal scaling with load balancer
- Monitor Redis memory usage
- Implement proper caching strategies

## Troubleshooting

### Common Issues

1. **EmptyResponseException**: TikTok is blocking requests
   - Solution: Use proxies or rotate MS tokens

2. **No healthy tokens available**: All MS tokens are invalid
   - Solution: Update MS tokens from TikTok cookies

3. **Rate limit exceeded**: Too many requests
   - Solution: Implement request queuing or increase rate limits

4. **Playwright browser issues**: Browser not installed
   - Solution: Run `poetry run playwright install`

### Logs

Check application logs for detailed error information:

```bash
# Docker logs
docker-compose logs tiktok-api

# Local development
# Logs are printed to console
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [TikTok-Api](https://github.com/davidteather/TikTok-Api) - The underlying TikTok API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - The web framework
- [Poetry](https://python-poetry.org/) - Dependency management
