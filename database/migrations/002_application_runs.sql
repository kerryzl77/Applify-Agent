-- Migration 002: Durable application runs, run steps, and artifacts

CREATE TABLE IF NOT EXISTS application_runs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    run_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'waiting_user', 'completed', 'failed', 'cancelled')),
    request_payload JSONB NOT NULL DEFAULT '{}',
    result_payload JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_application_runs_user_id ON application_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_application_runs_source ON application_runs(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_application_runs_status ON application_runs(status);
CREATE INDEX IF NOT EXISTS idx_application_runs_run_type ON application_runs(run_type);

CREATE TABLE IF NOT EXISTS run_steps (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES application_runs(id) ON DELETE CASCADE,
    step_key TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'waiting_user', 'completed', 'failed', 'skipped')),
    input_payload JSONB NOT NULL DEFAULT '{}',
    output_payload JSONB NOT NULL DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, step_key)
);

CREATE INDEX IF NOT EXISTS idx_run_steps_run_id ON run_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_run_steps_status ON run_steps(status);

CREATE TABLE IF NOT EXISTS artifacts (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    run_id TEXT REFERENCES application_runs(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    step_key TEXT,
    artifact_key TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('json', 'file')),
    format TEXT,
    payload_json JSONB,
    storage_backend TEXT,
    bucket_name TEXT,
    object_key TEXT,
    filename TEXT,
    content_type TEXT,
    size_bytes BIGINT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_source ON artifacts(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_key ON artifacts(artifact_key);
CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind);
