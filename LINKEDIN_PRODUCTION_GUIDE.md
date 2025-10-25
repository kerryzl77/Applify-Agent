# LinkedIn Playwright Scraper - Production Guide

## 🎯 Overview

This application uses **Playwright + GPT-4 Vision** to scrape LinkedIn profiles in production. This approach is:
- ✅ Simple and reliable
- ✅ No brittle DOM selectors
- ✅ Works with LinkedIn's current design
- ✅ Resilient to LinkedIn UI changes

## 🏗️ Architecture

```
LinkedIn Profile URL
        ↓
Playwright Browser (Chromium)
        ↓
Navigate + Screenshot
        ↓
GPT-4 Vision API
        ↓
Structured Profile Data
        ↓
LLM Email Generation
```

## 📋 Production Checklist

### ✅ Completed Setup

1. **Playwright Installation**
   - `playwright==1.48.0` added to `requirements.txt`
   - `bin/post_compile` script installs Chromium browser on Heroku
   - `Aptfile` provides system dependencies for Playwright

2. **Heroku Buildpacks** (in order)
   ```
   1. heroku-community/apt          # System dependencies
   2. heroku/python                  # Python runtime
   3. heroku/heroku-buildpack-libreoffice  # PDF generation
   ```

3. **Environment Variables**
   - ✅ `LINKEDIN_EMAIL` - LinkedIn account email
   - ✅ `LINKEDIN_PASSWORD` - LinkedIn account password
   - ✅ `PLAYWRIGHT_HEADLESS=true` - Run browser in headless mode
   - ✅ `OPENAI_API_KEY` - For GPT-4 Vision API

4. **Integration Verified**
   - ✅ LinkedIn scraper works locally
   - ✅ Data flows properly to LLM email generation
   - ✅ Profile data (name, company, skills) used in personalization

## 🔒 Current Authentication Strategy

**Approach**: Shared LinkedIn credentials (Developer Account)

**How it works**:
1. Application uses `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` from environment
2. Playwright logs in once and saves session to `./playwright-data/`
3. Subsequent requests reuse the session (faster, no re-login)
4. Session persists across requests but may expire after ~24 hours

**Limitations**:
- Single LinkedIn account for all users
- Subject to LinkedIn rate limits (~100 profile views/day)
- Account could be flagged if usage is excessive

## 🚀 Future Production Strategies (Not Implemented Yet)

### Option 1: User-Specific Credentials (Recommended for Scale)
Let each user provide their own LinkedIn credentials:
```python
# Store encrypted per-user LinkedIn credentials in database
user_linkedin_creds = db_manager.get_user_linkedin_creds(user_id)
scraper = LinkedInVisionScraper(
    email=user_linkedin_creds['email'],
    password=user_linkedin_creds['password']
)
```

**Benefits**:
- Each user has their own rate limits
- More scalable
- No shared account risk

**Implementation needed**:
- Add UI for users to enter LinkedIn credentials
- Encrypt credentials in database (use `cryptography` library)
- Modify scraper to accept per-user credentials

### Option 2: LinkedIn OAuth (Best for Production)
Use LinkedIn's official OAuth API:
- Most professional approach
- No password storage
- Official API rate limits
- Requires LinkedIn API app registration

**Not recommended because**:
- LinkedIn API has limited profile access compared to scraping
- Requires LinkedIn API approval (can take weeks)
- May not provide all needed profile data

## 📊 Monitoring & Best Practices

### Rate Limiting
- Current: 3-second delay between requests (configurable)
- LinkedIn limit: ~100 profile views/day per account
- Monitor for 451 errors (rate limit exceeded)

### Session Management
- Session saved to `./playwright-data/linkedin_session.json`
- On Heroku: Ephemeral filesystem means session resets on dyno restart
- Consider: Use Redis or database for persistent session storage

### Error Handling
- Scraper has fallback profile data if extraction fails
- GPT-4 Vision failures return minimal profile info
- Application continues to work with limited data

### Cost Optimization
```
Per LinkedIn Profile Scrape:
- Playwright: Free (just compute time ~5-10 seconds)
- GPT-4 Vision API: ~$0.01 per image (1920x1080 screenshot)
- Total: ~$0.01 per profile

For 1000 profiles/month: ~$10 in API costs
```

## 🛠️ Deployment Commands

```bash
# 1. Commit changes
git add .
git commit -m "Add LinkedIn Playwright scraper for production"

# 2. Deploy to Heroku
git push heroku main

# 3. Monitor logs
heroku logs --tail -a applify

# 4. Test LinkedIn scraping in production
curl -X POST https://applify-f333088ea507.herokuapp.com/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "hiring_manager_email",
    "person_name": "Zikai Liu",
    "person_position": "ML Engineer at Articula AI",
    "linkedin_url": "https://www.linkedin.com/in/zikailiu/",
    "recipient_email": "test@example.com"
  }'
```

## 🐛 Troubleshooting

### Issue: Playwright browsers not installed
**Symptom**: `Error: Executable doesn't exist at...`
**Fix**: Check `bin/post_compile` ran successfully in build logs
```bash
heroku logs --tail | grep "Installing Playwright"
```

### Issue: LinkedIn login fails
**Symptom**: `Login required` or `Could not find login form`
**Fix**:
1. Check credentials: `heroku config -a applify`
2. LinkedIn may require CAPTCHA/verification for new IPs
3. Try logging in manually from the Heroku IP first

### Issue: Session not persisting
**Symptom**: Re-login on every request
**Fix**: Heroku's ephemeral filesystem clears on restart
- Option A: Store session in Redis
- Option B: Accept re-login (adds ~5 seconds per request)

### Issue: GPT-4 Vision errors
**Symptom**: `Vision API error` in logs
**Fix**:
1. Check OpenAI API key: `heroku config:get OPENAI_API_KEY`
2. Verify API has GPT-4 Vision access
3. Check screenshot file size (should be < 20MB)

## 📈 Performance Metrics

**Expected Performance**:
- First request (with login): ~15-20 seconds
- Subsequent requests (cached session): ~10-15 seconds
- Breakdown:
  - Playwright navigation: 3-5 seconds
  - Screenshot + scroll: 2-3 seconds
  - GPT-4 Vision API: 5-10 seconds
  - Email generation: 2-5 seconds

## 🔐 Security Notes

1. **Credential Storage**: LinkedIn credentials stored as Heroku config vars (encrypted at rest)
2. **Session Security**: Session files contain auth tokens - use secure storage in production
3. **Rate Limiting**: Implement user-level rate limiting to prevent abuse
4. **Error Messages**: Don't expose LinkedIn credentials in error messages or logs

## 📚 Code Files

- `app/linkedin_vision_scraper.py` - Main scraper implementation
- `scraper/retriever.py` - Integration with data retrieval
- `app/llm_generator.py` - Email generation using LinkedIn data
- `test_simple_scraper.py` - Basic scraper test
- `test_linkedin_integration.py` - Full integration test
- `bin/post_compile` - Heroku build script for Playwright
- `Aptfile` - System dependencies for Playwright

## ✅ Testing Checklist

Before deploying:
- [ ] `python test_simple_scraper.py` passes locally
- [ ] `python test_linkedin_integration.py` passes locally
- [ ] LinkedIn credentials set in Heroku config
- [ ] Buildpacks configured correctly
- [ ] `bin/post_compile` is executable

After deploying:
- [ ] Check build logs for Playwright installation
- [ ] Test `/api/generate` endpoint with LinkedIn URL
- [ ] Monitor logs for any LinkedIn/Playwright errors
- [ ] Verify generated emails include LinkedIn profile data

## 🎓 Next Steps

1. **Monitor Usage**: Track LinkedIn scraping success rate
2. **Optimize Costs**: Cache frequently accessed profiles
3. **Scale**: Implement user-specific LinkedIn credentials
4. **Enhance**: Add more robust error handling for edge cases
5. **Analytics**: Track which LinkedIn fields are most useful for personalization

---

**Last Updated**: October 2025
**Status**: ✅ Ready for Production
**Deployment**: Heroku (applify-f333088ea507.herokuapp.com)
