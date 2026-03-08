# Backlog

Only the Orchestrator updates this file.

## Sprint 1: Foundation And Hardening

Goal: stabilize runtime flow, data contracts, and generation quality before UI polish.

- Map the repo and assign clear ownership lanes.
- Replace thread-based background work with worker jobs.
- Add `application_runs` and artifact persistence.
- Move uploaded/generated files to object storage.
- Harden auth and configuration handling.
- Define the canonical candidate profile schema.
- Tighten job normalization.
- Improve resume scoring, cover letter grounding, and evidence reuse.
- Write the one-command application package spec.
- Define acceptance criteria for resume, package, and outreach.
- Redesign the split dashboard/campaign journey at the spec level.
- Keep Frontend blocked until backend contracts are stable enough.

## Sprint 2: Runtime Integration

Goal: connect the new backend flow end to end and expose stable contracts for UI work.

- Land worker job orchestration and observability.
- Wire `application_runs` through job execution, artifact creation, and status reporting.
- Reuse one evidence model across resume, cover letter, and outreach drafts.
- Expose stable API contracts for package generation and campaign execution.
- Unblock Frontend on stable endpoints and response shapes.
- Build the first end-to-end happy path for one-command application packaging.

## Sprint 3: Product Polish And Launch Readiness

Goal: improve operator UX after the system is reliable and measurable.

- Implement the redesigned dashboard/campaign journey.
- Improve progress visibility, retry affordances, and artifact inspection.
- Refine output quality based on scoring feedback and acceptance criteria.
- Add regression coverage for core package and outreach flows.
- Tighten deployment, monitoring, and operational playbooks.

## Current Sequence

1. Hardening before polish
2. Contracts before frontend buildout
3. End-to-end package flow before secondary UX refinement
