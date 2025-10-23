# Applify - Heroku Deployment Guide

## 🚀 Quick Deploy

```bash
# 1. Stage your changes
git add .

# 2. Commit your changes
git commit -m "Your update message"

# 3. Deploy to Heroku
git push heroku main
```

## 🔍 Verify Setup

```bash
# Check you're logged in
heroku auth:whoami

# List your apps
heroku apps

# View app info
heroku apps:info -a applify

# Check environment variables
heroku config -a applify
```

## 📊 Monitor App

```bash
# View live logs
heroku logs --tail -a applify

# Check app status
heroku ps -a applify

# Open app in browser
heroku open -a applify
```

## 🔧 Troubleshooting

```bash
# Restart app
heroku restart -a applify

# Scale dynos
heroku ps:scale web=1 -a applify
```

**Live App:** https://applify-f333088ea507.herokuapp.com/

---
*For detailed setup, see [HEROKU_DEPLOY.md](HEROKU_DEPLOY.md)*
