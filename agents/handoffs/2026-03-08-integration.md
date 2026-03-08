# Integration Handoff

- agent: integration
- date: 2026-03-08

## Changed Files

- `.env.example`
- `Procfile`
- `agents/decisions.md`
- `agents/repo_map.md`
- `agents/specs/one-command-application-package.md`
- `app/agent/campaign_runner.py`
- `app/agent/draft_agent.py`
- `app/agent/evidence_agent.py`
- `app/cached_llm.py`
- `app/config.py`
- `app/document_intelligence.py`
- `app/document_intelligence_models.py`
- `app/llm_generator.py`
- `app/main.py`
- `app/object_storage.py`
- `app/redis_manager.py`
- `app/routers/agent.py`
- `app/routers/content.py`
- `app/run_dispatcher.py`
- `app/run_queue.py`
- `app/worker.py`
- `database/db_manager.py`
- `database/migrations/002_application_runs.sql`
- `requirements.txt`
- `tests/test_content_router.py`
- `tests/test_object_storage.py`

## What Landed

- Fixed generated-content cache correctness by keying on the full normalized request context instead of coarse company/title data.
- Cache hits now return the original `content_id`, `file_info`, and email fields, so artifact handles survive cached responses.
- Added durable run/step/artifact persistence, Redis-backed worker queue plumbing, and additive run inspection APIs for campaigns.
- Persisted generated content files through object-storage metadata and download lookup rather than relying only on formatter-local paths.
- Wired a shared typed candidate/job/evidence contract into live evidence generation and prompt construction while preserving legacy compatibility fields for current draft flows.

## Verification

- `python -m py_compile app/*.py app/agent/*.py app/routers/*.py database/*.py tests/*.py`
- `python -m unittest tests.test_content_router tests.test_object_storage` failed in this worktree because the local Python environment is missing `fastapi` and `pydantic-settings`

## Open Gaps / Risks

- Durable runs currently cover campaign execution; standalone cover-letter/email generation still persists artifacts durably but does not create an `application_run`.
- The shared evidence contract is now live in evidence and prompt-building paths, but resume tailoring still does not emit or consume the same durable run/artifact model.
- Existing draft generation still relies on compatibility fields like `why_me_bullets`; a second pass should remove that duplicate shape after downstream readers switch to the typed contract.
- End-to-end DB-backed/runtime tests were not runnable in this environment due missing dependencies.

## Recommended Next Step

- Use the new typed evidence contract to wire tailored resume generation into the same durable run/artifact flow, then add one DB-backed integration test that exercises `campaign -> evidence artifact -> run read API`.
