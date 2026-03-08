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
