# Agent Mission

This `agents/` workspace exists to coordinate parallel work on `job-application-llm` without stepping on the same files, losing context, or polishing the UI before the backend and generation pipeline are stable.

## Operating Model

- Orchestrator runs continuously and owns cycle planning, file ownership, and backlog updates.
- PM stays mostly in read, planning, and spec work.
- Full-stack and AI run in parallel by default.
- Frontend joins only when backend contracts are stable enough to implement against.
- Hardening comes before polish.

## Hard Rules

- Only Orchestrator updates `agents/backlog.md`.
- All agents append decisions to `agents/decisions.md`; no rewrites of prior entries.
- Every coding agent writes a short handoff note in `agents/handoffs/` at the end of its cycle.
- No two coding agents touch the same files in the same cycle.
- Each agent works in its own git worktree.
- Orchestrator assigns file ownership before coding starts in a cycle.
- If a contract is still moving, Frontend waits and PM/Full-stack/AI continue to converge the interface first.

## Parallelism Rule

Use this default lane setup:

- Orchestrator: continuously
- PM: mostly read, plan, and spec
- Full-stack and AI: in parallel
- Frontend: only after backend contracts are stable enough

This is the highest-leverage setup for this repo because the near-term bottlenecks are infrastructure, data model, runtime flow, and generation quality rather than pure surface polish.

## First Ownership

### Orchestrator first

- Create the repo map
- Define the three-sprint backlog
- Sequence hardening before polish

### PM first

- Write the one-command application package spec
- Define acceptance criteria for resume, package, and outreach
- Redesign the current split dashboard/campaign journey

### Full-stack first

- Replace threads with worker jobs
- Add `application_runs` and artifacts
- Move files to object storage
- Harden auth and config

### AI first

- Define the canonical candidate profile schema
- Tighten job normalization
- Improve tailored resume scoring and cover letter grounding
- Make outreach drafts pull from the same evidence model

## Cycle Protocol

1. Orchestrator opens the cycle, assigns owners, and records file boundaries.
2. PM updates specs and acceptance criteria without colliding with coding files.
3. Full-stack and AI execute in parallel within their assigned file sets.
4. Frontend starts only after Orchestrator marks the relevant contracts stable.
5. Each coding agent writes a short handoff note before the cycle closes.
