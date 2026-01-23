# Applify - AI Job Application Assistant

## Production Status: ✅ DEPLOYED

**Live URL:** https://applify-f333088ea507.herokuapp.com/

---

## Architecture Overview

```
FastAPI (Python) + React SPA
├── Backend API (/api/*)     ← FastAPI with JWT auth
├── Frontend (/)             ← React SPA (served from client/dist/)
├── PostgreSQL               ← User data, profiles
└── Redis                    ← Caching, session state
```

**Deployment:** Single Heroku dyno (container stack)
**Server:** Uvicorn ASGI with 2 workers

---

## Project Structure

```
job-application-llm/
├── app/                          # FastAPI Backend
│   ├── main.py                   # App entry point, router registration
│   ├── config.py                 # Settings (JWT, CORS, env vars)
│   ├── schemas.py                # Pydantic models for request/response
│   ├── security.py               # JWT token creation/validation, password hashing
│   ├── dependencies.py           # FastAPI dependencies (get_current_user, db)
│   │
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py           # Router exports
│   │   ├── auth.py               # /api/auth/* (login, register, logout, refresh)
│   │   ├── content.py            # /api/generate (AI content generation)
│   │   ├── resume.py             # /api/upload-resume, /api/refine-resume
│   │   └── gmail.py              # /api/gmail/* (OAuth, drafts)
│   │
│   ├── llm_generator.py          # OpenAI GPT integration for content
│   ├── universal_extractor.py    # Job posting & LinkedIn scraping
│   ├── resume_parser.py          # PDF/DOCX resume parsing
│   ├── resume_refiner.py         # AI-powered resume tailoring
│   ├── advanced_resume_generator.py  # Enhanced resume generation
│   ├── fast_pdf_generator.py     # PDF output generation
│   ├── gmail_service.py          # Gmail API integration
│   ├── redis_manager.py          # Redis caching layer
│   ├── cached_llm.py             # LLM response caching
│   └── background_tasks.py       # Async task processing
│
├── client/                       # React Frontend
│   ├── src/
│   │   ├── App.jsx               # Root component, routing
│   │   ├── main.jsx              # Entry point
│   │   ├── components/           # Reusable UI components
│   │   │   ├── ContentGenerator.jsx  # Main content gen interface
│   │   │   ├── ResumeUploader.jsx    # Resume upload/parsing
│   │   │   ├── Sidebar.jsx           # Navigation
│   │   │   ├── ProfileModal.jsx      # User profile editor
│   │   │   ├── GmailSetup.jsx        # Gmail OAuth setup
│   │   │   └── Toast.jsx             # Notifications
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx     # Main app page
│   │   │   ├── Login.jsx         # Login form
│   │   │   └── Register.jsx      # Registration form
│   │   ├── services/
│   │   │   └── api.js            # Axios client with JWT interceptors
│   │   ├── store/
│   │   │   └── useStore.js       # Zustand state (auth, profile, theme)
│   │   └── utils/
│   │       └── helpers.js        # Utility functions
│   ├── dist/                     # Production build (committed for Heroku)
│   └── package.json
│
├── database/
│   └── db_manager.py             # PostgreSQL connection pooling, CRUD
│
├── scraper/
│   ├── retriever.py              # Web content extraction
│   └── url_validator.py          # URL validation
│
├── config/
│   └── gcp-oauth.keys.template.json  # Gmail OAuth template
│
├── Dockerfile                    # Container definition
├── Procfile                      # Heroku process: uvicorn
├── heroku.yml                    # Heroku container config
├── requirements.txt              # Python dependencies
└── .gitignore                    # Production-safe ignores
```

---

## Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI 0.109+ | Async Python API |
| Server | Uvicorn | ASGI server |
| Auth | python-jose (JWT) | Token-based authentication |
| Validation | Pydantic | Request/response schemas |
| Database | PostgreSQL | User data, profiles |
| Cache | Redis | Response caching, rate limiting |
| AI | OpenAI GPT-4 | Content generation |

### Frontend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 19 | UI library |
| Build | Vite 7 | Bundler |
| Styling | Tailwind CSS 4 | Utility CSS |
| State | Zustand | Global state |
| HTTP | Axios | API client |
| Routing | React Router | SPA navigation |

---

## Authentication Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Client    │      │   FastAPI   │      │  PostgreSQL │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │ POST /api/auth/login                    │
       │ {email, password}  │                    │
       │───────────────────>│                    │
       │                    │ Verify credentials │
       │                    │───────────────────>│
       │                    │<───────────────────│
       │                    │                    │
       │ {access_token,     │                    │
       │  token_type,       │                    │
       │  expires_in}       │                    │
       │<───────────────────│                    │
       │                    │                    │
       │ Set-Cookie:        │                    │
       │ refresh_token      │                    │
       │ (httpOnly)         │                    │
       │                    │                    │
       │ GET /api/* with    │                    │
       │ Authorization:     │                    │
       │ Bearer <token>     │                    │
       │───────────────────>│                    │
       │                    │ Validate JWT       │
       │                    │ (dependencies.py)  │
       │                    │                    │
```

**Token Storage:**
- Access token: In-memory (Zustand store)
- Refresh token: HTTP-only cookie
- Expiry: Access 30min, Refresh 7 days

---

## API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | No | Create account |
| POST | `/login` | No | Get tokens (OAuth2 form) |
| POST | `/refresh` | Cookie | Refresh access token |
| POST | `/logout` | Yes | Clear refresh cookie |
| GET | `/check` | Yes | Validate current token |

### Content Generation (`/api`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/generate` | Yes | Generate job app content |
| POST | `/validate-url` | Yes | Validate job/LinkedIn URL |

**Generate Request Schema:**
```python
class GenerateContentRequest(BaseModel):
    content_type: str  # 'linkedin_message', 'connection_email', 'cover_letter', 'hiring_manager_email'
    input_type: str    # 'url' or 'manual'
    url: Optional[str]
    manual_text: Optional[str]
    person_name: Optional[str]
    recipient_email: Optional[EmailStr]
```

### Resume Management (`/api`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/upload-resume` | Yes | Upload & parse resume |
| GET | `/resume-progress/{task_id}` | Yes | Check parsing progress |
| POST | `/refine-resume` | Yes | Tailor resume to job |
| GET | `/resume-refine-progress/{task_id}` | Yes | Check refinement progress |
| GET | `/download-resume/{task_id}` | Yes | Download refined resume |

### Profile (`/api`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/candidate-data` | Yes | Get user profile |
| POST | `/update-candidate-data` | Yes | Update profile |

### Gmail (`/api/gmail`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/status` | Yes | Check Gmail connection |
| GET | `/auth-url` | Yes | Get OAuth URL |
| GET | `/oauth2callback` | No | OAuth callback |
| POST | `/create-draft` | Yes | Create email draft |
| POST | `/disconnect` | Yes | Revoke Gmail access |

### Health
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | DB & Redis status |

---

## Environment Variables

### Required (Heroku Config Vars)
```bash
# Core
OPENAI_API_KEY=sk-...              # OpenAI API key
DATABASE_URL=postgres://...         # Auto-set by Heroku Postgres
REDIS_URL=rediss://...              # Auto-set by Heroku Redis

# JWT Authentication
JWT_SECRET_KEY=<base64-random>      # Token signing key
ALGORITHM=HS256                     # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30      # Access token TTL
REFRESH_TOKEN_EXPIRE_DAYS=7         # Refresh token TTL

# URLs
APP_BASE_URL=https://applify-xxx.herokuapp.com
FRONTEND_ORIGIN=https://applify-xxx.herokuapp.com

# Gmail OAuth (optional)
GCP_OAUTH_KEYS={"web":{...}}        # Google OAuth credentials JSON
GMAIL_REDIRECT_URI=https://applify-xxx.herokuapp.com/api/gmail/oauth2callback

```

---

## Key Files Reference

### Entry Points
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, middleware, router registration |
| `client/src/main.jsx` | React app entry |

### Core Logic
| File | Purpose |
|------|---------|
| `app/llm_generator.py` | OpenAI prompts for content types |
| `app/universal_extractor.py` | Job/LinkedIn data extraction |
| `app/resume_refiner.py` | Resume tailoring logic |

### Authentication
| File | Purpose |
|------|---------|
| `app/security.py` | `create_access_token()`, `decode_token()`, `hash_password()` |
| `app/dependencies.py` | `get_current_user()` dependency |
| `app/routers/auth.py` | Auth endpoints |

### State Management
| File | Purpose |
|------|---------|
| `client/src/store/useStore.js` | Zustand: user, tokens, profile, theme |
| `client/src/services/api.js` | Axios with JWT interceptor |

---

## Deployment

### Heroku (Current)
```bash
# Deploy
git push heroku main

# View logs
heroku logs --tail -a applify

# Check config
heroku config -a applify

# Restart
heroku restart -a applify
```

### Local Development
```bash
# Backend
cd job-application-llm
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 5000

# Frontend
cd client
npm install && npm run dev
```

---

## Content Generation Types

| Type | Output | Max Length |
|------|--------|------------|
| `linkedin_message` | Connection request | 200 chars |
| `connection_email` | Intro email | 200 words |
| `hiring_manager_email` | Direct outreach | 200 words |
| `cover_letter` | Formal letter | 350 words |
| `tailored_resume` | PDF resume | Full document |

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### User Data (JSON in candidate_data)
```python
{
    "personal_info": {"name", "email", "phone", "linkedin", "github"},
    "resume": {"summary", "experience[]", "education[]", "skills[]"},
    "story_bank": [{"title", "story"}],
    "templates": {"linkedin_messages", "connection_emails", ...},
    "gmail_tokens": {...}  # Encrypted OAuth tokens
}
```

---

## Error Handling

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request / validation error |
| 401 | Unauthorized (invalid/expired token) |
| 404 | Not found |
| 500 | Server error |

### Frontend Error Flow
```javascript
// api.js interceptor
if (error.response?.status === 401) {
    // Try token refresh
    // If refresh fails → logout → redirect /login
}
```

---

## Security Measures

- ✅ JWT tokens with expiry
- ✅ HTTP-only refresh token cookie
- ✅ Password hashing (SHA-256)
- ✅ CORS whitelist
- ✅ Input validation (Pydantic)
- ✅ SQL parameterization
- ✅ No secrets in git

---

**Last Updated:** January 22, 2026
**Version:** 3.0.0 (FastAPI + JWT)
**Status:** ✅ PRODUCTION
