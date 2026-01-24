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
│   │   ├── content.py            # /api/content/* (AI content generation)
│   │   ├── resume.py             # /api/resume/* (upload, refine, progress)
│   │   ├── gmail.py              # /api/gmail/* (OAuth, drafts)
│   │   ├── jobs.py               # /api/jobs/* (job discovery, feed, extract)
│   │   └── agent.py              # /api/agent/* (campaign workflow)
│   │
│   ├── agent/                    # Multi-agent campaign system
│   │   ├── campaign_runner.py    # Orchestrates campaign workflow
│   │   ├── draft_agent.py        # Generates email/message drafts
│   │   ├── evidence_agent.py     # Collects supporting evidence
│   │   ├── research_agent.py     # Researches contacts/companies
│   │   ├── scheduler_agent.py    # Schedules follow-ups
│   │   └── sse.py                # Server-sent events for streaming
│   │
│   ├── jobs/                     # ATS job ingestion
│   │   ├── ats_scrapers.py       # Greenhouse/Ashby scrapers
│   │   └── ingest_daily.py       # Scheduled job refresh
│   │
│   ├── search/                   # Web search integration
│   │   └── openai_web_search.py  # OpenAI-powered search
│   │
│   ├── utils/                    # Utility modules
│   │   └── text.py               # Text normalization helpers
│   │
│   ├── llm_generator.py          # OpenAI GPT integration for content
│   ├── cached_llm.py             # LLM response caching
│   ├── universal_extractor.py    # Job posting & LinkedIn scraping
│   │
│   ├── # === 2-Tier Resume Pipeline ===
│   ├── resume_extractor_pymupdf.py   # Tier 1: PyMuPDF layout extraction
│   ├── resume_rewriter_vlm.py        # Tier 2: GPT-5.2 VLM structured parsing
│   ├── one_page_fitter.py            # Deterministic one-page fitting
│   ├── enhanced_resume_processor.py  # Background upload processing (uses Tier 1+2)
│   ├── fast_pdf_generator.py         # PDF output generation
│   ├── output_formatter.py           # Content formatting and DOCX/PDF
│   │
│   ├── gmail_service.py          # Gmail API integration
│   └── redis_manager.py          # Redis caching layer
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
│   │   │   ├── JobDetailDrawer.jsx   # Job details slide-over
│   │   │   ├── LoadingSpinner.jsx    # Loading indicator
│   │   │   └── Toast.jsx             # Notifications
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx     # Main app page
│   │   │   ├── DiscoverJobs.jsx  # Job discovery feed
│   │   │   ├── Campaign.jsx      # Campaign workflow UI
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
│   ├── db_manager.py             # PostgreSQL connection pooling, CRUD
│   └── migrations/               # SQL migration files
│       └── 001_jobs_tables.sql   # Jobs discovery schema
│
├── data/
│   └── job_seeds.json            # ATS company sources seed data
│
├── scraper/
│   ├── retriever.py              # Web content extraction
│   └── url_validator.py          # URL validation
│
├── config/
│   └── gcp-oauth.keys.template.json  # Gmail OAuth template
│
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Local dev environment
├── Procfile                      # Heroku process: uvicorn
├── heroku.yml                    # Heroku container config
├── requirements.txt              # Python dependencies
├── runtime.txt                   # Python version spec
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
       │  refresh_token,    │                    │
       │  token_type}       │                    │
       │<───────────────────│                    │
       │                    │                    │
       │ Store tokens       │                    │
       │ (Zustand store)    │                    │
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
- Refresh token: Client-stored (returned in login response)
- Expiry: Access 15min (default), Refresh 7 days

---

## API Endpoints

### Authentication (`/api/auth`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | No | Create account, returns tokens |
| POST | `/login` | No | Get tokens (JSON body) |
| POST | `/refresh` | No | Refresh tokens (body: refresh_token) |
| POST | `/logout` | Yes | Logout (stateless, client clears tokens) |
| GET | `/check` | Yes | Validate current token |
| GET | `/me` | Yes | Get current user info |

### Content Generation (`/api/content`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/generate` | Yes | Generate job app content |
| POST | `/validate-url` | Yes | Validate job/LinkedIn URL |
| GET | `/candidate-data` | Yes | Get user profile |
| POST | `/candidate-data` | Yes | Update user profile |
| GET | `/download/{file_path}` | Yes | Download generated file |
| GET | `/convert-to-pdf/{file_path}` | Yes | Convert DOCX to PDF |

**Generate Request Schema:**
```python
class GenerateContentRequest(BaseModel):
    content_type: str  # 'linkedin_message', 'connection_email', 'cover_letter', 'hiring_manager_email'
    input_type: str    # 'url' or 'manual'
    url: Optional[str]
    manual_text: Optional[str]
    person_name: Optional[str]
    person_position: Optional[str]
    linkedin_url: Optional[str]
    recipient_email: Optional[str]
```

### Resume Management (`/api/resume`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/upload` | Yes | Upload & parse resume |
| GET | `/progress` | Yes | Check parsing progress |
| POST | `/clear-progress` | Yes | Clear processing status |
| POST | `/refine` | Yes | Tailor resume to job |
| GET | `/refinement-progress/{task_id}` | Yes | Check refinement progress |
| POST | `/analysis` | Yes | Analyze resume vs job (no refinement) |
| GET | `/download/{file_path}` | Yes | Download refined resume |

### Gmail (`/api/gmail`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/status` | Yes | Check Gmail connection |
| GET | `/auth-url` | Yes | Get OAuth URL |
| GET | `/oauth2callback` | No | OAuth callback (redirects to frontend) |
| POST | `/create-draft` | Yes | Create email draft |
| POST | `/disconnect` | Yes | Revoke Gmail access |

### Jobs Discovery (`/api/jobs`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/feed` | Yes | Paginated job feed with filters |
| GET | `/{job_id}` | Yes | Get job details (optional JD extraction) |
| POST | `/extract` | Yes | Extract job from external URL |
| POST | `/{job_id}/save` | Yes | Save job to user's list |
| POST | `/{job_id}/start-campaign` | Yes | Start campaign for job |
| POST | `/refresh` | Yes | Trigger ATS ingestion |
| GET | `/refresh/status` | Yes | Get ingestion progress |
| GET | `/refresh/stream` | Yes | SSE stream for ingestion progress |

### Campaign Agent (`/api/agent`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/campaigns/{id}` | Yes | Get campaign with state |
| POST | `/campaigns/{id}/run` | Yes | Start campaign workflow |
| GET | `/campaigns/{id}/events` | Yes | SSE stream for campaign events |
| POST | `/campaigns/{id}/feedback` | Yes | Add feedback for regeneration |
| POST | `/campaigns/{id}/confirm` | Yes | Confirm & create Gmail drafts |

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
JWT_SECRET_KEY=<base64-random>      # Token signing key (or SECRET_KEY)
JWT_ALGORITHM=HS256                 # JWT algorithm (default: HS256)
ACCESS_TOKEN_EXPIRE_MINUTES=15      # Access token TTL (default: 15)
REFRESH_TOKEN_EXPIRE_DAYS=7         # Refresh token TTL (default: 7)

# URLs
PUBLIC_URL=https://applify-xxx.herokuapp.com
FRONTEND_ORIGIN=https://applify-xxx.herokuapp.com
ALLOWED_ORIGINS=https://applify-xxx.herokuapp.com  # CORS whitelist

# Gmail OAuth (optional)
GCP_OAUTH_KEYS={"web":{...}}        # Google OAuth credentials JSON

# App Settings
DEBUG=false                         # Enable/disable docs endpoints
ENVIRONMENT=production              # 'production' or 'development'
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
| `app/cached_llm.py` | LLM with Redis caching |
| `app/universal_extractor.py` | Job/LinkedIn data extraction |
| `app/output_formatter.py` | DOCX/PDF formatting |

### Resume Pipeline (2-Tier VLM Architecture)
| File | Purpose |
|------|---------|
| `app/resume_extractor_pymupdf.py` | Tier 1: PyMuPDF layout-aware extraction |
| `app/resume_rewriter_vlm.py` | Tier 2: GPT-5.2 VLM structured parsing/tailoring |
| `app/one_page_fitter.py` | Deterministic one-page constraint enforcement |
| `app/enhanced_resume_processor.py` | Background upload processing (orchestrates Tier 1+2) |
| `app/fast_pdf_generator.py` | High-performance PDF generation |

### Authentication
| File | Purpose |
|------|---------|
| `app/security.py` | `create_access_token()`, `decode_token()`, `hash_password()` |
| `app/dependencies.py` | `get_current_user()` dependency |
| `app/routers/auth.py` | Auth endpoints |

### Jobs & Campaigns
| File | Purpose |
|------|---------|
| `app/routers/jobs.py` | Job discovery feed, extraction, saving |
| `app/routers/agent.py` | Campaign workflow endpoints |
| `app/agent/campaign_runner.py` | Orchestrates multi-agent campaign |
| `app/jobs/ats_scrapers.py` | Greenhouse/Ashby job scrapers |

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

## Resume Pipeline Architecture (2-Tier VLM)

The resume upload and tailoring pipeline uses a 2-tier architecture for robust handling of complex PDF layouts.

### Architecture Overview

```
Upload Flow:
  PDF/DOCX → Tier 1 (PyMuPDF) → Tier 2 (GPT-5.2 VLM) → Profile DB

Refine Flow:
  Profile + Job Desc → VLM Tailoring → One-Page Fitter → PDF Generator
```

### Tier 1: PyMuPDF Extraction (`resume_extractor_pymupdf.py`)
- **Purpose**: Fast, deterministic layout extraction
- **Output**:
  - `pages[].blocks[]`: Text blocks with bbox, font stats, heading candidates
  - `fulltext_linear`: Reading-order text
  - `page_images[]`: Base64 PNG of first page for VLM vision

### Tier 2: GPT-5.2 VLM (`resume_rewriter_vlm.py`)
- **Purpose**: Structured JSON parsing using vision + text
- **Features**:
  - Uses OpenAI Responses API with Pydantic structured outputs
  - No regex JSON parsing needed (strict schema enforcement)
  - Two modes: `parse_resume()` for upload, `tailor_resume()` for refinement
- **Output Schema**:
  - `personal_info`: name, email, phone, location, linkedin, github, website
  - `resume`: summary (str), skills (flat list), experience[], education[]
  - `story_bank`: STAR-format achievement stories (for upload)

### One-Page Fitter (`one_page_fitter.py`)
- **Purpose**: Deterministic constraint enforcement for one-page resumes
- **Constraints**:
  - Max 4 experience roles, 3 bullets each
  - Max 15 skills
  - Summary limited to ~60 words
  - Progressive compression if still too long

### Key Endpoints
| Endpoint | Description |
|----------|-------------|
| `POST /api/resume/upload` | Upload resume, triggers Tier 1+2 processing |
| `GET /api/resume/progress` | Poll for upload processing status |
| `POST /api/resume/refine` | Tailor resume to job description |
| `GET /api/resume/refinement-progress/{task_id}` | Poll refinement status |
| `GET /api/resume/download/{file}` | Download generated PDF |

### Data Flow

1. **Upload**: User uploads PDF → `enhanced_resume_processor` → Tier 1 extracts layout + image → Tier 2 VLM parses to structured JSON → Merged into `user_profiles.profile_data`
2. **Refine**: User provides job description → Load profile + cached extraction artifacts → VLM tailors content → One-page fitter applies constraints → `fast_pdf_generator` creates PDF → Download

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

## Jobs Discovery System

### ATS Support
- **Greenhouse**: API-based job board scraping
- **Ashby**: API-based job board scraping
- **External URLs**: Any job posting URL via universal extractor

### Campaign Workflow
1. **Research Phase**: Identify contacts, gather company intel
2. **Draft Phase**: Generate personalized emails/messages
3. **Review Phase**: User feedback and regeneration
4. **Confirm Phase**: Create Gmail drafts, schedule follow-ups

### Multi-Agent Architecture
| Agent | Purpose |
|-------|---------|
| Research Agent | Find hiring managers, recruiters, referrers |
| Evidence Agent | Collect supporting data for personalization |
| Draft Agent | Generate tailored outreach content |
| Scheduler Agent | Plan follow-up sequences |
| Campaign Runner | Orchestrate workflow, manage state |

---

## Database Schema

### Core User Tables
```sql
-- Users (authentication)
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- User Profiles (JSONB candidate data)
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    profile_data JSONB NOT NULL
);

-- Generated Content History
CREATE TABLE generated_content (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    content_type TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- Gmail OAuth Tokens
CREATE TABLE gmail_auth (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMP NOT NULL,
    scope TEXT DEFAULT '',
    email TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Jobs Discovery Tables
```sql
-- ATS Company Sources (curated list)
CREATE TABLE ats_company_sources (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    ats_type TEXT NOT NULL,        -- 'greenhouse', 'ashby'
    board_root_url TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    tags TEXT[] DEFAULT '{}',
    last_success_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job Posts (from ATS or user-pasted URLs)
CREATE TABLE job_posts (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,     -- 'ats', 'external'
    company_source_id INTEGER REFERENCES ats_company_sources(id),
    created_by_user_id TEXT REFERENCES users(id),
    company_name TEXT NOT NULL,
    ats_type TEXT NOT NULL,        -- 'greenhouse', 'ashby', 'external'
    title TEXT NOT NULL,
    location TEXT,
    team TEXT,
    employment_type TEXT,
    url TEXT UNIQUE NOT NULL,
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    hash TEXT,
    raw_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Saved Jobs
CREATE TABLE user_saved_jobs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_post_id INTEGER NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'saved',  -- 'saved', 'campaign_started', 'archived'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_post_id)
);

-- Job Campaigns (workflow state)
CREATE TABLE job_campaigns (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_post_id INTEGER NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
    state JSONB DEFAULT '{}',      -- Campaign workflow state
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schema Migrations Tracking
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Profile Data Structure (JSONB in user_profiles)
```python
{
    "personal_info": {"name", "email", "phone", "linkedin", "github"},
    "resume": {"summary", "experience[]", "education[]", "skills[]"},
    "story_bank": [{"title", "story"}],
    "templates": {"linkedin_messages", "connection_emails", ...}
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

- ✅ JWT tokens with expiry (access + refresh)
- ✅ Password hashing (SHA-256)
- ✅ CORS whitelist
- ✅ Input validation (Pydantic)
- ✅ SQL parameterization (psycopg2)
- ✅ No secrets in git
- ✅ Gmail OAuth state validation via Redis

---

**Last Updated:** January 23, 2026
**Version:** 2.0.0 (FastAPI + JWT + Jobs Discovery)
**Status:** ✅ PRODUCTION
