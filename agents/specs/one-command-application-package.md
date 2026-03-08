# One-Command Application Package Spec

## Goal

Let a user trigger one command or one primary UI action that produces an application package for a target job using shared candidate evidence and reusable artifacts.

## User Outcome

For a selected job, the system should generate a consistent package containing:

- tailored resume
- grounded cover letter
- supporting artifacts or evidence bundle
- outreach draft that cites the same evidence model

## Product Requirements

- One primary entrypoint kicks off the full package flow.
- The flow runs asynchronously and exposes run status.
- Generated outputs share the same candidate profile and evidence basis.
- Artifacts are persisted and re-openable after generation completes.
- Failures are visible per step and support retry without losing the full run context.

## Acceptance Criteria

### Resume

- Tailoring reflects the selected job's core requirements.
- Output is based on the canonical candidate profile schema.
- Claims in the resume are traceable to source evidence.
- Final artifact is exportable and stored with the run.

### Package

- A single run produces a durable `application_run` record plus linked artifacts.
- Package generation exposes step-level status and terminal state.
- Package outputs are retrievable without recomputing the entire run.
- Storage is object-store friendly rather than dependent on local-only files.

### Outreach

- Outreach drafts reuse the same evidence model as resume and cover letter generation.
- Drafts are grounded in job- and candidate-specific facts rather than generic copy.
- The user can inspect the evidence basis for the draft.
- Outreach can be regenerated without mutating unrelated package artifacts.

## Journey Redesign

Replace the current split dashboard/campaign journey with:

1. Select or ingest job
2. Review normalized job brief
3. Launch one-command package run
4. Inspect run progress and artifacts in one place
5. Approve or refine outputs
6. Trigger outreach from the same evidence-backed package

## Dependencies

- Full-stack: worker jobs, `application_runs`, artifact persistence, object storage
- AI: candidate schema, normalization, scoring, grounding, shared evidence model
- Frontend: waits until the API contract and artifact shapes stabilize

## Current Backend Scope After 2026-03-08 Integration

- Landed now:
  - durable campaign runs with `application_runs`, `run_steps`, and run-read APIs
  - persisted generated-content file artifacts with object-storage-friendly download lookup
  - shared typed candidate/job/evidence contract wired into evidence generation and prompt building
  - corrected generated-content cache behavior that preserves artifact handles on cache hits

- Not landed yet:
  - tailored resume generation as a durable run artifact
  - package compilation step that bundles resume, cover letter, and outreach under one run
  - frontend workspace migration onto the new run/artifact contract

- Interpretation:
  - the backend now supports durable campaign execution and durable standalone content artifacts
  - the full one-command application package remains a staged follow-up, not a completed claim
