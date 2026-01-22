# Heroku Deployment Guide

## Quick Setup Commands

```bash
# 1. Install Heroku CLI and login
heroku login

# 2. Create new Heroku app
heroku create your-app-name

# 3. Set stack to container for Docker deployment
heroku stack:set container -a your-app-name

# 4. Add required addons
heroku addons:create heroku-postgresql:mini -a your-app-name
heroku addons:create heroku-redis:mini -a your-app-name

# 5. Set environment variables
heroku config:set OPENAI_API_KEY=your_api_key_here -a your-app-name
heroku config:set JWT_SECRET_KEY=$(openssl rand -base64 32) -a your-app-name
heroku config:set ENVIRONMENT=production -a your-app-name

# Optional: Google Custom Search for enhanced LinkedIn scraping
heroku config:set GOOGLE_CSE_API_KEY=your_google_cse_api_key -a your-app-name
heroku config:set GOOGLE_CSE_CX=your_google_cse_cx_id -a your-app-name

# Optional: Gmail OAuth (for email drafts feature)
heroku config:set GCP_OAUTH_KEYS='<base64-encoded-oauth-config>' -a your-app-name
heroku config:set GMAIL_REDIRECT_URI=https://your-app-name.herokuapp.com/api/gmail/oauth2callback -a your-app-name

# 6. Deploy from GitHub
# Connect your GitHub repo in Heroku dashboard, then:
git push heroku main
```

## Required Environment Variables

Set these in Heroku dashboard or via CLI:

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `JWT_SECRET_KEY` - Secret for signing JWT tokens (generate with: `openssl rand -base64 32`)
- `ENVIRONMENT=production`

**Optional (for enhanced LinkedIn scraping):**
- `GOOGLE_CSE_API_KEY` - Google Custom Search Engine API key
- `GOOGLE_CSE_CX` - Google Custom Search Engine ID (CX)

**Optional (for Gmail integration):**
- `GCP_OAUTH_KEYS` - Base64-encoded Google OAuth client configuration
- `GMAIL_REDIRECT_URI` - OAuth callback URL (e.g., `https://your-app.herokuapp.com/api/gmail/oauth2callback`)

Without Google CSE, the system will fall back to DuckDuckGo search.

## Automatic Variables (Set by Heroku)

These are automatically populated by addons:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection  
- `PORT` - App port

## Build Frontend Before Deploying

The frontend must be built before deploying:

```bash
cd client
npm install
npm run build
cd ..
git add client/dist
git commit -m "Build frontend for production"
```

## Scaling

```bash
# Scale web dynos
heroku ps:scale web=1 -a your-app-name

# View logs
heroku logs --tail -a your-app-name
```

## Health Check

Your app includes a health endpoint at `/health` that monitors:
- Database connectivity
- Redis connectivity
- Overall app status

## API Documentation

In development mode, FastAPI provides automatic API documentation:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

Note: API docs are disabled in production for security.

## Cost Optimization

- **Hobby tier**: ~$16/month (Hobby Postgres + Redis)
- **Free tier**: Use free addons if available
- **Production**: Upgrade to Standard tier addons

## Troubleshooting

1. **Build fails**: Check `heroku logs --tail`
2. **Database issues**: Ensure `DATABASE_URL` is set
3. **Redis issues**: Ensure `REDIS_URL` is set
4. **Permission errors**: Dockerfile runs as non-root user
5. **Authentication issues**: Verify `JWT_SECRET_KEY` is set
6. **CORS issues**: Set `ALLOWED_ORIGINS` to your frontend domain if needed

## Architecture

This application uses:
- **Backend**: FastAPI with JWT authentication
- **Frontend**: React + Vite + Tailwind CSS
- **Database**: PostgreSQL
- **Cache**: Redis
- **ASGI Server**: Uvicorn
