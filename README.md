# Applify - AI Job Application Agent

> **Your job search, orchestrated.** Multi-agent system for personalized job outreach — from resume to inbox.

[![Watch Demo](https://img.youtube.com/vi/Z5MpDQYWKaY/maxresdefault.jpg)](https://youtu.be/Z5MpDQYWKaY)

🎬 **[Watch Demo (90s)](https://youtu.be/Z5MpDQYWKaY)** · 🚀 **[Try Live App](https://applify-f333088ea507.herokuapp.com/)**

---

## 🚀 Deployment

Production deploys from GitHub Actions after CI passes on `main`.

```bash
# Emergency/manual fallback only
git push heroku main
```

Configure these GitHub repository secrets before enabling deploys:

- `HEROKU_API_KEY`
- `HEROKU_APP_NAME=applify`
- `HEROKU_EMAIL`

CI runs backend tests, frontend lint/build, and a full Docker build on pull requests and pushes to `main`.

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

---
*For detailed setup, see [HEROKU_DEPLOY.md](HEROKU_DEPLOY.md)*
