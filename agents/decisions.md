# Decisions

Append-only log. Every agent adds new entries at the bottom with date, owner, and rationale.

## 2026-03-07 - bootstrap - Multi-agent operating model

- Adopted an Orchestrator-led workflow with PM, Full-stack, AI, and conditional Frontend lanes.
- Chosen because the repo's immediate leverage is in infrastructure, data model, runtime flow, and generation quality.

## 2026-03-07 - bootstrap - File ownership and worktree isolation

- Each coding agent must work in a separate git worktree.
- No two coding agents may touch the same files during the same cycle.
- Chosen to reduce merge collisions and ambiguous ownership during parallel execution.

## 2026-03-07 - bootstrap - Backlog and handoff policy

- `agents/backlog.md` is owned by Orchestrator only.
- Every coding agent must leave a short handoff note in `agents/handoffs/`.
- Chosen to keep planning centralized while preserving execution context between cycles.

## 2026-03-08 - integration - Cache keys must reflect full generation context

- Generated-content caching now keys off the full normalized request context instead of only company/title.
- Cache payloads must preserve `content_id`, `file_info`, and email fields so cache hits do not orphan artifact handles.
- Chosen because correctness and artifact retrievability matter more than early cache hits during scraping/parsing.

## 2026-03-08 - integration - Durable runs are additive compatibility layer

- `application_runs`, `run_steps`, and `artifacts` are the canonical backend records for new campaign executions and generated files.
- `job_campaigns.state` remains a compatibility projection for the current SSE/UI path until product contracts stabilize further.
- Chosen to land durable execution/storage now without forcing premature frontend migration.

## 2026-03-08 - integration - Shared evidence contract wired through live generators

- Live evidence generation now emits a typed candidate/job/evidence contract and outreach/cover-letter prompts consume that same normalized basis.
- Legacy convenience fields such as `why_me_bullets` remain in the payload temporarily for compatibility with existing draft flows.
- Chosen to improve grounding immediately while avoiding a destabilizing all-at-once rewrite.
