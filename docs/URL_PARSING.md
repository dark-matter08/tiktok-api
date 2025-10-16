# TikTok URL Parsing Feature

## Overview

The TikTok API Backend now supports automatic extraction of video IDs from various TikTok URL formats. This feature makes it easier to work with TikTok videos by accepting URLs directly instead of requiring manual ID extraction.

## Supported URL Formats

The API recognizes and parses the following TikTok URL formats:

### 1. Standard URL Format
```
https://www.tiktok.com/@username/video/1234567890123456789
https://tiktok.com/@username/video/1234567890123456789
```

### 2. Short URLs (vm.tiktok.com)
```
https://vm.tiktok.com/ZMxxx/
```
**Note**: Requires redirect resolution to extract the video ID.

### 3. Alternative Short Format
```
https://www.tiktok.com/t/ZMxxx/
https://tiktok.com/t/ZMxxx/
```
**Note**: Requires redirect resolution to extract the video ID.

## API Endpoints

### 1. Parse Video URL (Dedicated Endpoint)

**Endpoint**: `POST /api/v1/video/parse-url`

Extract a video ID from a TikTok URL without fetching video information.

**Request Body**:
```json
{
  "url": "https://www.tiktok.com/@username/video/1234567890123456789",
  "resolve_redirects": true
}
```

**Parameters**:
- `url` (string, required): The TikTok video URL
- `resolve_redirects` (boolean, optional, default: true): Whether to resolve shortened URLs

**Response**:
```json
{
  "video_id": "1234567890123456789",
  "original_url": "https://www.tiktok.com/@username/video/1234567890123456789",
  "resolved_url": null,
  "timestamp": "2025-10-16T12:00:00.000000"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/video/parse-url" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://www.tiktok.com/@username/video/1234567890123456789",
    "resolve_redirects": true
  }'
```

### 2. Get Video Info (Smart Parameter Detection)

**Endpoint**: `GET /api/v1/video/{video_id}`

This endpoint now accepts both video IDs and URLs. The API automatically detects the format and extracts the ID if needed.

**Usage with Video ID**:
```bash
GET /api/v1/video/1234567890123456789
```

**Usage with URL (URL-encoded)**:
```bash
GET /api/v1/video/https%3A%2F%2Fwww.tiktok.com%2F%40username%2Fvideo%2F1234567890123456789
```

**cURL Examples**:

With video ID:
```bash
curl "http://localhost:8000/api/v1/video/1234567890123456789" \
  -H "X-API-Key: your-api-key"
```

With URL:
```bash
VIDEO_URL="https://www.tiktok.com/@username/video/1234567890123456789"
ENCODED_URL=$(echo -n "$VIDEO_URL" | jq -sRr @uri)

curl "http://localhost:8000/api/v1/video/$ENCODED_URL" \
  -H "X-API-Key: your-api-key"
```

## Implementation Details

### URL Parsing Logic

The URL parser uses regex patterns to extract video IDs:

1. **Standard URL Pattern**: Matches `@username/video/{video_id}` format
2. **Short URL Detection**: Identifies `vm.tiktok.com` and `tiktok.com/t/` URLs
3. **Redirect Resolution**: Uses HTTP HEAD requests to follow redirects without downloading content

### Short URL Resolution

When `resolve_redirects=true` (default), the API:
1. Makes an HTTP HEAD request to the short URL
2. Follows redirects automatically (max 5 redirects)
3. Extracts the video ID from the final URL
4. Times out after 10 seconds

### Performance Considerations

- **Standard URLs**: Instant extraction (regex-based)
- **Short URLs**: 100-500ms additional latency for redirect resolution
- **Caching**: Consider implementing client-side caching for repeated URLs

## Error Handling

### Common Errors

**Invalid URL Format**:
```json
{
  "detail": "Unable to extract video ID from URL: invalid-url",
  "status_code": 400
}
```

**Resolution Timeout**:
```json
{
  "detail": "Failed to parse video URL: timeout",
  "status_code": 500
}
```

**Invalid Video ID**:
```json
{
  "detail": "Video '1234567890123456789' not found",
  "status_code": 404
}
```

## Best Practices

### 1. Use the Appropriate Endpoint

- **For just extracting IDs**: Use `POST /api/v1/video/parse-url`
- **For getting video info**: Use `GET /api/v1/video/{video_id}` (accepts both IDs and URLs)

### 2. Handle Short URLs Efficiently

If you know the URL is a short URL, set `resolve_redirects=true` explicitly:
```json
{
  "url": "https://vm.tiktok.com/ZMxxx/",
  "resolve_redirects": true
}
```

### 3. URL Encoding

Always URL-encode URLs when passing them as path parameters:

**Python**:
```python
from urllib.parse import quote

url = "https://www.tiktok.com/@user/video/123"
encoded = quote(url, safe='')
endpoint = f"/api/v1/video/{encoded}"
```

**JavaScript**:
```javascript
const url = "https://www.tiktok.com/@user/video/123";
const encoded = encodeURIComponent(url);
const endpoint = `/api/v1/video/${encoded}`;
```

**Bash**:
```bash
VIDEO_URL="https://www.tiktok.com/@user/video/123"
ENCODED=$(echo -n "$VIDEO_URL" | jq -sRr @uri)
```

### 4. Error Handling

Always handle both 400 (bad URL) and 404 (video not found) errors:

```python
try:
    response = requests.post(
        "http://api/v1/video/parse-url",
        json={"url": tiktok_url},
        headers={"X-API-Key": api_key}
    )
    response.raise_for_status()
    video_id = response.json()["video_id"]
except requests.HTTPError as e:
    if e.response.status_code == 400:
        print("Invalid URL format")
    else:
        print(f"Error: {e}")
```

## Examples

### Example 1: Extract ID from Standard URL

```bash
curl -X POST "http://localhost:8000/api/v1/video/parse-url" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://www.tiktok.com/@charlidamelio/video/7123456789012345678"
  }'
```

Response:
```json
{
  "video_id": "7123456789012345678",
  "original_url": "https://www.tiktok.com/@charlidamelio/video/7123456789012345678",
  "resolved_url": null,
  "timestamp": "2025-10-16T12:00:00.000000"
}
```

### Example 2: Get Video Info with URL

```bash
curl "http://localhost:8000/api/v1/video/https%3A%2F%2Fwww.tiktok.com%2F%40user%2Fvideo%2F7123456789012345678" \
  -H "X-API-Key: your-api-key"
```

### Example 3: Resolve Short URL

```bash
curl -X POST "http://localhost:8000/api/v1/video/parse-url" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://vm.tiktok.com/ZMxxx/",
    "resolve_redirects": true
  }'
```

## Security Considerations

1. **Rate Limiting**: URL parsing endpoints have rate limits (100-150 requests/minute)
2. **Redirect Safety**: Only follows HTTPS redirects to tiktok.com domains
3. **Timeout Protection**: HTTP requests timeout after 10 seconds
4. **Input Validation**: URLs are validated before processing

## Troubleshooting

### Issue: "Unable to extract video ID"

**Cause**: The URL format is not recognized or is malformed.

**Solution**: Verify the URL format matches one of the supported patterns.

### Issue: Slow Response Times

**Cause**: Short URL resolution requires HTTP requests.

**Solution**: 
- Cache resolved IDs on the client side
- Use standard URLs when possible
- Set `resolve_redirects=false` if you know it's a standard URL

### Issue: 404 Not Found

**Cause**: The video ID is valid but the video doesn't exist or is private.

**Solution**: Handle 404 errors gracefully in your application.

## Future Enhancements

Potential improvements for this feature:

1. **Caching**: Cache resolved short URLs to improve performance
2. **Batch Processing**: Support multiple URLs in a single request
3. **Additional Formats**: Support more TikTok URL variations
4. **Resolved URL Return**: Include the resolved full URL in responses
5. **Analytics**: Track which URL formats are most commonly used

## Support

For issues or questions about URL parsing:
- Check the API documentation at `/docs`
- Review error messages carefully
- Ensure URLs are properly encoded
- Verify API key authentication is working

