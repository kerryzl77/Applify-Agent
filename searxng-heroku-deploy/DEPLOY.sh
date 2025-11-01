#!/bin/bash
set -e

echo "========================================="
echo "SearXNG Heroku Deployment Script"
echo "========================================="
echo ""

# Configuration
SEARXNG_APP_NAME="${1:-applify-searxng}"
MAIN_APP_NAME="${2:-applify}"

echo "Configuration:"
echo "  SearXNG app name: $SEARXNG_APP_NAME"
echo "  Main app name: $MAIN_APP_NAME"
echo ""

# Step 1: Create Heroku app for SearXNG
echo "Step 1: Creating Heroku app for SearXNG..."
if heroku apps:info -a "$SEARXNG_APP_NAME" >/dev/null 2>&1; then
    echo "  ✅ App $SEARXNG_APP_NAME already exists"
else
    heroku create "$SEARXNG_APP_NAME"
    echo "  ✅ Created app: $SEARXNG_APP_NAME"
fi

# Step 2: Set container stack
echo ""
echo "Step 2: Setting container stack..."
heroku stack:set container -a "$SEARXNG_APP_NAME"
echo "  ✅ Container stack enabled"

# Step 3: Initialize git repo if needed
echo ""
echo "Step 3: Preparing deployment files..."
if [ ! -d .git ]; then
    git init
    echo "  ✅ Git initialized"
else
    echo "  ✅ Git already initialized"
fi

# Step 4: Add Heroku remote
echo ""
echo "Step 4: Adding Heroku remote..."
if git remote | grep -q "^searxng$"; then
    git remote remove searxng
fi
heroku git:remote -a "$SEARXNG_APP_NAME" -r searxng
echo "  ✅ Remote 'searxng' added"

# Step 5: Commit files
echo ""
echo "Step 5: Committing deployment files..."
git add .
git commit -m "Deploy SearXNG to Heroku" --allow-empty
echo "  ✅ Files committed"

# Step 6: Deploy to Heroku
echo ""
echo "Step 6: Deploying to Heroku (this may take 3-5 minutes)..."
git push searxng main --force

# Step 7: Wait for deployment
echo ""
echo "Step 7: Waiting for deployment to complete..."
sleep 10

# Step 8: Verify deployment
echo ""
echo "Step 8: Verifying SearXNG instance..."
SEARXNG_URL="https://${SEARXNG_APP_NAME}.herokuapp.com"
echo "  Testing: $SEARXNG_URL/search?q=test&format=json"

if curl -sS -m 10 "$SEARXNG_URL/search?q=test&format=json" | grep -q "results"; then
    echo "  ✅ SearXNG is working!"
else
    echo "  ⚠️  SearXNG may not be ready yet. Check logs:"
    echo "     heroku logs --tail -a $SEARXNG_APP_NAME"
fi

# Step 9: Configure main app
echo ""
echo "Step 9: Configuring main app to use SearXNG..."
heroku config:set SEARXNG_URL="$SEARXNG_URL" -a "$MAIN_APP_NAME"
echo "  ✅ SEARXNG_URL set in main app"

# Step 10: Summary
echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "SearXNG Instance:"
echo "  URL: $SEARXNG_URL"
echo "  Test: $SEARXNG_URL/search?q=test&format=json"
echo "  Logs: heroku logs --tail -a $SEARXNG_APP_NAME"
echo ""
echo "Main App Configuration:"
echo "  App: $MAIN_APP_NAME"
echo "  SEARXNG_URL: $SEARXNG_URL"
echo ""
echo "Next Steps:"
echo "  1. Test SearXNG: curl '$SEARXNG_URL/search?q=python&format=json'"
echo "  2. Redeploy main app: cd ../.. && git push heroku main"
echo "  3. Verify integration: heroku logs --tail -a $MAIN_APP_NAME | grep SearXNG"
echo ""
