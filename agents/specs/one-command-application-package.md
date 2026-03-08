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
I 