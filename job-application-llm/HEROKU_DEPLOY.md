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
heroku config:set SECRET_KEY=$(openssl rand -base64 32) -a your-app-name
heroku config:set FLASK_ENV=production -a your-app-name

# 6. Deploy from GitHub
# Connect your GitHub repo in Heroku dashboard, then:
git push heroku main
```

## Required Environment Variables

Set these in Heroku dashboard or via CLI:

- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Flask secret key (generate with: `openssl rand -base64 32`)
- `FLASK_ENV=production`

## Automatic Variables (Set by Heroku)

These are automatically populated by addons:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection  
- `PORT` - App port

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

## Cost Optimization

- **Hobby tier**: ~$16/month (Hobby Postgres + Redis)
- **Free tier**: Use free addons if available
- **Production**: Upgrade to Standard tier addons

## Troubleshooting

1. **Build fails**: Check `heroku logs --tail`
2. **Database issues**: Ensure `DATABASE_URL` is set
3. **Redis issues**: Ensure `REDIS_URL` is set  
4. **Permission errors**: Dockerfile runs as non-root user