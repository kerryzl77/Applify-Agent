# SearXNG Production Deployment for Heroku

## Quick Start (Automated)

```bash
cd searxng-heroku-deploy

# Login to Heroku first
heroku login

# Run automated deployment script
./DEPLOY.sh applify-searxng applify
```

This will:
1. Create a new Heroku app `applify-searxng`
2. Deploy SearXNG as a Docker container
3. Configure your main app `applify` to use it
4. Verify everything works

---

## Manual Step-by-Step Deployment

### Prerequisites

```bash
# Ensure you're logged in to Heroku
heroku login

# Navigate to deployment directory
cd searxng-heroku-deploy
```

### Step 1: Create SearXNG Heroku App

```bash
# Create new app (choose a unique name)
heroku create applify-searxng

# Set to container stack (required for Docker)
heroku stack:set container -a applify-searxng
```

### Step 2: Initialize Git Repository

```bash
# Initialize git if not already done
git init

# Add all deployment files
git add .

# Commit
git commit -m "Deploy SearXNG to Heroku"
```

### Step 3: Add Heroku Remote and Deploy

```bash
# Add Heroku remote
heroku git:remote -a applify-searxng -r searxng

# Deploy (this takes 3-5 minutes)
git push searxng main
```

**Expected output:**
```
remote: Building source:
remote: === Fetching app code
remote: === Building web (Dockerfile)
remote: Successfully built <image-id>
remote: Successfully tagged <tag>
remote: Verifying deploy... done.
To https://git.heroku.com/applify-searxng.git
 * [new branch]      main -> main
```

### Step 4: Verify SearXNG is Working

```bash
# Wait 10 seconds for app to start
sleep 10

# Test the search endpoint
curl "https://applify-searxng.herokuapp.com/search?q=test&format=json"
```

**Expected:** JSON response with `"results": [...]`

### Step 5: Configure Main App

```bash
# Set SEARXNG_URL in your main application
heroku config:set SEARXNG_URL=https://applify-searxng.herokuapp.com -a applify

# Verify configuration
heroku config:get SEARXNG_URL -a applify
```

### Step 6: Deploy Main App

```bash
# Navigate back to main app directory
cd /Users/liuzikai/Documents/GitHub/Applify-Agent/job-application-llm

# Push to Heroku (your changes are already committed)
git push heroku main
```

### Step 7: Verify Integration

```bash
# Check logs for SearXNG usage
heroku logs --tail -a applify | grep "SearXNG"
```

**Expected log output:**
```
Using custom SearXNG instance from SEARXNG_URL: https://applify-searxng.herokuapp.com
Cache enabled: max_size=100, ttl=600s
🔍 Searching SearXNG: "John Doe" site:linkedin.com/in
✅ SearXNG (https://applify-searxng.herokuapp.com) returned 5 results
```

---

## Troubleshooting

### SearXNG app won't start

```bash
# Check logs
heroku logs --tail -a applify-searxng

# Restart
heroku ps:restart -a applify-searxng
```

### Search returns empty results

```bash
# Test directly
curl -v "https://applify-searxng.herokuapp.com/search?q=python&format=json"

# Check if limiter is blocking (should be disabled in settings.yml)
heroku config -a applify-searxng
```

### Main app not using SearXNG

```bash
# Verify env var is set
heroku config:get SEARXNG_URL -a applify

# Should output: https://applify-searxng.herokuapp.com

# If not set:
heroku config:set SEARXNG_URL=https://applify-searxng.herokuapp.com -a applify

# Restart main app
heroku ps:restart -a applify
```

---

## Cost

**Heroku Pricing:**
- **Eco Dynos** ($5/month for both apps, shared across all apps)
- **Basic Dynos** ($7/month per app = $14/month total)

**Compared to Google CSE:**
- 1k queries/day = ~$150/month with Google CSE
- **Savings: $135-145/month**

---

## Scaling

### For 10k+ queries/day

```bash
# Upgrade to larger dyno
heroku ps:scale web=1:standard-1x -a applify-searxng

# Or deploy multiple instances in different regions
heroku create applify-searxng-eu
# ... repeat deployment steps for EU instance

# Configure main app to use both
heroku config:set SEARXNG_INSTANCES=https://applify-searxng.herokuapp.com,https://applify-searxng-eu.herokuapp.com -a applify
```

---

## Files in This Directory

```
searxng-heroku-deploy/
├── DEPLOY.sh           # Automated deployment script
├── Dockerfile          # SearXNG container configuration
├── heroku.yml          # Heroku container deployment config
├── settings.yml        # SearXNG settings (limiter disabled, JSON enabled)
└── README.md           # This file
```

---

## Security Notes

1. **Change the secret key** in `settings.yml` before deploying to production
2. The limiter is **disabled** for your app's use - only your app should know the URL
3. Consider using Heroku's **Private Spaces** for true isolation (Enterprise plan)

---

## Monitoring

```bash
# Monitor SearXNG usage
heroku logs --tail -a applify-searxng

# Monitor main app SearXNG integration
heroku logs --tail -a applify | grep SearXNG

# Check dyno status
heroku ps -a applify-searxng
```

---

## Maintenance

### Updating SearXNG

```bash
cd searxng-heroku-deploy

# Rebuild and redeploy (pulls latest searxng/searxng:latest)
git commit --allow-empty -m "Rebuild SearXNG"
git push searxng main --force
```

### Backup Configuration

```bash
# Backup current settings
heroku run cat /etc/searxng/settings.yml -a applify-searxng > settings-backup.yml
```
