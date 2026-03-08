# Repo Map

## Product Shape

`job-application-llm` is an AI-assisted job application system with a Python backend, a React frontend, database migrations, artifact generation, and outreach/campaign workflows.

## Top-Level Areas

- `app/`: FastAPI application, routers, agent workflows, LLM services, resume/artifact generation, auth, and background job logic.
- `client/`: React 19 + Vite frontend for the dashboard and campaign/user flows.
- `database/`: database access code, migrations, and candidate data fixtures.
- `tests/`: backend-oriented regression tests.
- `scraper/`: retrieval and URL validation helpers.
- `config/`, `data/`, `uploads/`, `output/`: environment/config inputs and local file outputs.

## High-Value Backend Areas

- `app/main.py`: FastAPI entrypoint.
- `app/routers/`: HTTP routes including jobs, auth, resume, content, Gmail, and agent endpoints.
- `app/agent/`: research, drafting, scheduling, campaign running, evidence, and SSE-related flows.
- `app/llm_service.py`, `app/llm_generator.py`, `app/cached_llm.py`: generation and model integration layer.
- `app/artifact_models.py`, `app/output_formatter.py`, `app/fast_pdf_generator.py`: artifact shaping and export.
- `app/security.py`, `app/dependencies.py`, `app/config.py`: auth and runtime configuration.

## High-Value Data Areas

- `database/db_manager.py`: database access boundary.
- `database/migrations/001_jobs_tables.sql`: current schema baseline.
- Future likely hotspot: new `application_runs` and artifact persistence tables.

## High-Value Frontend Area

- `client/package.json`: React/Vite app with routing, state, animation, markdown, and toast support.
- Frontend should stay downstream of stable backend contracts for application packaging and campaign flow.

## Likely First Parallel Lanes

- Orchestrator: `agents/` coordination files and cycle ownership.
- PM: `agents/specs/` and UX/acceptance planning docs.
- Full-stack: worker jobs, persistence, object storage, auth/config, and route integration.
- AI: candidate schema, normalization, scoring, grounding, and shared evidence model.
- Frontend: deferred until API and artifact contracts stop moving.
