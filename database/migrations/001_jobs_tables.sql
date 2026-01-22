-- Migration 001: Jobs discovery tables
-- Create tables for ATS job board ingestion and user job tracking

-- Table: ats_company_sources
-- Curated list of ATS job board roots (Greenhouse, Ashby)
CREATE TABLE IF NOT EXISTS ats_company_sources (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    ats_type TEXT NOT NULL CHECK (ats_type IN ('greenhouse', 'ashby')),
    board_root_url TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    tags TEXT[] DEFAULT '{}',
    last_success_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for filtering by ATS type
CREATE INDEX IF NOT EXISTS idx_ats_sources_ats_type ON ats_company_sources(ats_type);
CREATE INDEX IF NOT EXISTS idx_ats_sources_is_active ON ats_company_sources(is_active);

-- Table: job_posts
-- Normalized job cards from ATS ingestion or user-pasted URLs
CREATE TABLE IF NOT EXISTS job_posts (
    id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN ('ats', 'external')),
    company_source_id INTEGER REFERENCES ats_company_sources(id) ON DELETE SET NULL,
    created_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    external_job_id TEXT,
    company_name TEXT NOT NULL,
    ats_type TEXT NOT NULL CHECK (ats_type IN ('greenhouse', 'ashby', 'external')),
    title TEXT NOT NULL,
    location TEXT,
    team TEXT,
    employment_type TEXT,
    url TEXT UNIQUE NOT NULL,
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    hash TEXT,
    raw_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_job_posts_source_type ON job_posts(source_type);
CREATE INDEX IF NOT EXISTS idx_job_posts_ats_type ON job_posts(ats_type);
CREATE INDEX IF NOT EXISTS idx_job_posts_company_name ON job_posts(company_name);
CREATE INDEX IF NOT EXISTS idx_job_posts_title ON job_posts(title);
CREATE INDEX IF NOT EXISTS idx_job_posts_location ON job_posts(location);
CREATE INDEX IF NOT EXISTS idx_job_posts_last_seen ON job_posts(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_job_posts_created_by_user ON job_posts(created_by_user_id);

-- Table: user_saved_jobs
-- Tracks which jobs users have saved or started campaigns for
CREATE TABLE IF NOT EXISTS user_saved_jobs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_post_id INTEGER NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'saved' CHECK (status IN ('saved', 'campaign_started', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, job_post_id)
);

-- Indexes for user_saved_jobs
CREATE INDEX IF NOT EXISTS idx_user_saved_jobs_user_id ON user_saved_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_saved_jobs_status ON user_saved_jobs(status);

-- Table: job_campaigns
-- Stub table for campaign state tracking (future expansion)
CREATE TABLE IF NOT EXISTS job_campaigns (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_post_id INTEGER NOT NULL REFERENCES job_posts(id) ON DELETE CASCADE,
    state JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for job_campaigns
CREATE INDEX IF NOT EXISTS idx_job_campaigns_user_id ON job_campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_job_campaigns_job_post_id ON job_campaigns(job_post_id);
