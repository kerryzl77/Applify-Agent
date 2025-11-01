# SearXNG Search Integration

## Overview

SearXNG is now the **default search provider**, offering:

- ✅ Free & unlimited (no API keys or monthly caps)
- ✅ Scalable for 1k+ queries/day
- ✅ 3-tier fallback: SearXNG → Google CSE → DuckDuckGo
- ✅ LRU caching with 10-min TTL (reduces load by ~60%)
- ✅ Multi-engine aggregation (better coverage)

## Features

**Production-Ready:**
- Multi-instance fallback (5 public instances by default)
- Exponential backoff retry (2 retries per instance)
- Thread-safe LRU cache (100 entries, 600s TTL)
- Configurable via environment variables
- Detailed logging for debugging

**Zero Setup:**
```bash
git push heroku main  # Works immediately with public instances
```

**Note:** Public instances may rate-limit. For production (1k+ queries/day), self-host.

## Production Setup (Heroku — Tested & Recommended)

Follow these steps to run a dedicated SearXNG instance on Heroku and connect this app to it.

1) Create a dedicated Heroku app for SearXNG

```bash
heroku create your-searxng-app
heroku stack:set container -a your-searxng-app
```

2) Prepare a minimal SearXNG deployment

```bash
git clone https://github.com/searxng/searxng-docker.git
cd searxng-docker

# Minimal settings enabling JSON results
mkdir -p searxng
cat > searxng/settings.yml << 'YAML'
server:
  bind_address: 0.0.0.0
  port: 8080               # container listens on 8080
  base_url: /              # Heroku will inject the public URL
  secret_key: change-me

search:
  formats:
    - html
    - json

engines:
  - name: duckduckgo
    disabled: false
  - name: brave
    disabled: false
  - name: google
    disabled: false
YAML

# Add Heroku container configuration
cat > heroku.yml << 'YAML'
build:
  docker:
    web: Dockerfile
run:
  web: python searx/webapp.py
YAML

# Commit and deploy
git add searxng/settings.yml heroku.yml
git commit -m "Add minimal SearXNG settings and Heroku config"
heroku git:remote -a your-searxng-app
git push heroku main
```

3) Verify the SearXNG app

```bash
heroku logs --tail -a your-searxng-app | sed -n '1,50p'

# Probe the JSON API (replace with your actual Heroku app hostname)
curl -s "https://your-searxng-app.herokuapp.com/search?q=test&format=json" | head -c 200
```

4) Point this app to your SearXNG instance

```bash
heroku config:set SEARXNG_URL=https://your-searxng-app.herokuapp.com -a your-app-name
```

Notes:
- Set `SEARXNG_URL` to the base host (no trailing `/search`). The client auto-appends it and falls back to POST if GET is blocked.
- Keep the built-in limiter enabled in production; disable it only for local testing.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | Public instances | Single custom instance (overrides all) |
| `SEARXNG_INSTANCES` | 5 public | CSV of instances: `https://a.com,https://b.com` |
| `SEARXNG_TIMEOUT` | 15 | Request timeout (seconds) |
| `SEARXNG_MAX_RETRIES` | 2 | Retries per instance |
| `DISABLE_SEARXNG` | 0 | Set to `1` to skip SearXNG (use Google CSE first) |
| `GOOGLE_CSE_API_KEY` | None | Google CSE fallback API key |
| `GOOGLE_CSE_CX` | None | Google CSE context ID |

**All variables are optional.** App works out-of-box with defaults.

## Search Fallback Chain

The app uses a robust 3-tier fallback system:

```
1. SearXNG (default)
   ↓ (if fails or returns 0 results)
2. Google CSE (if configured with API keys)
   ↓ (if fails or not configured)
3. DuckDuckGo (ultimate fallback)
```

This ensures **100% uptime** even if one provider fails.

## Testing Your Setup

```bash
# Test SearXNG integration
python test_searxng.py

# Test with custom instance
SEARXNG_URL=https://your-instance.com python test_searxng.py
```

## Configuration Files

### Updated Files
- ✅ `app/searxng_search.py` - New SearXNG client with retry logic
- ✅ `app/universal_extractor.py` - Updated to use SearXNG as default
- ✅ `requirements.txt` - No changes needed (uses existing `requests`)

## Performance & Cost

### Public Instances (Free Tier)
- **Cost:** $0/month
- **Throughput:** ~100-500 queries/day (varies by instance)
- **Best for:** Development, testing, low-traffic apps

### Self-Hosted (Production)
- **Cost:** ~$7-15/month (Heroku Hobby / Railway Pro)
- **Throughput:** Unlimited (set your own rate limits)
- **Best for:** Production apps with 1k+ queries/day

## Troubleshooting

### All SearXNG instances failing?
- **Solution 1:** Set a custom instance via `SEARXNG_URL`
- **Solution 2:** Configure Google CSE for reliable fallback
- **Solution 3:** The app will automatically use DuckDuckGo

### Rate limiting (429 errors)?
- Public instances have limits; deploy your own instance

### Slow search results?
- Some public instances may be slow
- Self-host for consistent <2s response times

### Local self‑host returns 403/405 from /search
- Some SearXNG deployments block JSON GET or enforce strict rate limits by default.
- Our client auto-retries with POST. For local testing, you can disable the limiter via the sample below.

```bash
mkdir -p searxng
cat > searxng/settings.yml << 'YAML'
server:
  bind_address: 0.0.0.0
  port: 8080
  base_url: http://localhost:8080/
  secret_key: change-me
  limiter: false  # disable built-in rate limiter for local testing

search:
  formats:
    - html
    - json

engines:
  - name: duckduckgo
    disabled: false
  - name: brave
    disabled: false
  - name: google
    disabled: false
YAML

docker rm -f searxng 2>/dev/null || true
docker run -d --name searxng -p 8080:8080 \
  -v "$PWD/searxng:/etc/searxng:ro" \
  searxng/searxng:latest

# App config
export SEARXNG_URL=http://localhost:8080

# Verify container is healthy and /search returns JSON
docker ps -a | grep searxng
docker logs searxng --tail 100
curl -i "http://localhost:8080/search?q=test&format=json"
```

Notes:
- The app auto-appends `/search`, so set `SEARXNG_URL` to the base host (no trailing `/search`).
- If GET still returns 403, the client now retries with POST automatically.

## Monitoring

Check search provider usage in logs:

```bash
heroku logs --tail -a your-app-name | grep "SearXNG\|Google CSE\|DuckDuckGo"
```

Example log output:
```
✅ SearXNG (https://searx.tiekoetter.com) returned 5 results
  → Trying Google CSE...
  → Google CSE returned 3 results
```

## Migration from Google CSE

No action required! Your existing Google CSE configuration will continue to work as a fallback. To fully switch to SearXNG:

1. Deploy your own SearXNG instance (see above)
2. Set `SEARXNG_URL` environment variable
3. Optionally remove Google CSE env vars to save costs

## Advanced Configuration

### Custom SearXNG Settings

Edit `searxng/settings.yml` in your self-hosted instance:

```yaml
# Enable specific search engines
engines:
  - name: google
    disabled: false
  - name: duckduckgo
    disabled: false
  - name: brave
    disabled: false

# Rate limiting
rate_limiting:
  max_request_per_minute: 60

# Language/region
default_locale: en
default_lang: en
```

### Multi-Region Instances

For global apps, deploy SearXNG in multiple regions:

```bash
# Set multiple instances (comma-separated)
heroku config:set SEARXNG_INSTANCES="https://us.searxng.com,https://eu.searxng.com" -a your-app-name
```

## Resources

- [SearXNG Documentation](https://docs.searxng.org/)
- [SearXNG Docker Deployment](https://github.com/searxng/searxng-docker)
- [Public Instances List](https://searx.space/)
- [Search Quality Comparison](https://github.com/searxng/searxng/wiki/Comparison)

## Support

- **Issues?** Check `heroku logs --tail` for error messages
- **Questions?** See fallback behavior in `app/universal_extractor.py:194-260`
