# Heroku Deployment Guide

## Recommended Deployment Flow

Use GitHub Actions as the primary deployment path:

1. Push or merge to `main`
2. GitHub Actions runs backend tests, frontend lint/build, and a Docker image build
3. If CI passes, GitHub Actions pushes the container image to Heroku and releases it

Required GitHub repository secrets:

- `HEROKU_API_KEY`
- `HEROKU_APP_NAME=applify`
- `HEROKU_EMAIL`

Keep runtime application config in Heroku config vars rather than GitHub Actions.

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

# Optional: Gmail OAuth (for email drafts feature)
heroku config:set GCP_OAUTH_KEYS='<base64-encoded-oauth-config>' -a your-app-name
heroku config:set GMAIL_REDIRECT_URI=https://your-app-name.herokuapp.com/api/gmail/oauth2callback -a your-app-name

# 6. Optional emergency/manual deploy
git push heroku main
```

## Required Environment Variables

Set these in Heroku dashboard or via CLI:

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `JWT_SECRET_KEY` - Secret for signing JWT tokens (generate with: `openssl rand -base64 32`)
- `ENVIRONMENT=production`

**Optional (for Gmail integration):**
- `GCP_OAUTH_KEYS` - Base64-encoded Google OAuth client configuration
- `GMAIL_REDIRECT_URI` - OAuth callback URL (e.g., `https://your-app.herokuapp.com/api/gmail/oauth2callback`)

## Automatic Variables (Set by Heroku)

These are automatically populated by addons:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection  
- `PORT` - App port

## Frontend Build

The Docker image builds the frontend during image creation. Production deploys no longer depend on committing `client/dist`.

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
