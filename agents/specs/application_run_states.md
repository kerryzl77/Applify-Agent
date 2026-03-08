# Application Run States

## Purpose

Define the product-visible lifecycle for an `application_run` so backend, AI, and frontend can implement one shared mental model.

This state model should replace the current split between content generation status and campaign status.

## Core Object

`application_run` is the top-level record for one user and one target job.

It owns:

- job source and normalized brief
- candidate evidence snapshot
- artifact generation steps
- review states
- export readiness
- outreach readiness

## Product State Model

### Run-Level States

#### `draft`

Meaning:

- job is ingested or selected
- run has not started yet

User-facing copy:

- `Ready to create your application package`

Allowed actions:

- inspect job brief
- fix missing resume/profile issue
- launch run
- discard draft

#### `queued`

Meaning:

- run request accepted
- waiting for worker execution

User-facing copy:

- `Starting your application package`

Allowed actions:

- leave screen safely
- cancel if execution has not materially started

#### `running`

Meaning:

- at least one generation step is active

User-facing copy:

- `Building your application package`

Allowed actions:

- monitor progress
- leave and return later
- optionally cancel remaining unfinished steps

#### `needs_review`

Meaning:

- all required artifacts generated
- one or more artifacts should be reviewed before the package is considered approved

User-facing copy:

- `Your package is ready for review`

Allowed actions:

- review artifacts
- accept all
- revise one artifact
- export
- use outreach drafts

#### `ready`

Meaning:

- required artifacts are accepted or auto-accepted
- package is complete

User-facing copy:

- `Application package ready`

Allowed actions:

- export artifacts
- copy/share drafts
- regenerate selected artifacts
- archive run

#### `partial`

Meaning:

- run completed with at least one optional artifact failure
- required core package still exists

User-facing copy:

- `Package ready with some missing extras`

Allowed actions:

- review completed artifacts
- retry failed optional steps
- export available package

#### `failed`

Meaning:

- a required step failed and no acceptable package is available

User-facing copy:

- `We couldn’t finish this package`

Allowed actions:

- retry failed step
- restart run from job brief
- inspect failure reason

#### `canceled`

Meaning:

- user or system stopped the run before completion

User-facing copy:

- `Package creation stopped`

Allowed actions:

- restart run
- keep any completed artifacts if policy allows
- archive run

#### `archived`

Meaning:

- run is no longer active in primary lists

Allowed actions:

- reopen
- duplicate for a new run

## Step-Level States

Each step in the run should expose its own status:

- `not_started`
- `running`
- `done`
- `failed`
- `skipped`
- `blocked`

## Required Steps

These steps determine whether the package is fundamentally successful:

1. `job_brief_ready`
2. `candidate_evidence_ready`
3. `resume_tailored`
4. `cover_letter_generated`
5. `package_compiled`

If any required step fails, the run cannot become `ready`.

## Optional Steps

These steps improve package completeness but should not block the primary promise:

1. `outreach_drafts_generated`
2. `gmail_drafts_created`
3. `contact_suggestions_ready`

If optional steps fail, the run may still become `partial` or `ready`.

## Recommended Step Order

1. `job_ingested`
2. `job_brief_ready`
3. `candidate_evidence_ready`
4. `resume_tailored`
5. `cover_letter_generated`
6. `outreach_drafts_generated`
7. `package_compiled`

This order reflects product priority:

- resume first
- cover letter second
- outreach third

## Review States

Each artifact should have an independent review state:

- `unreviewed`
- `accepted`
- `needs_changes`

Recommended defaults:

- tailored resume starts as `unreviewed`
- cover letter starts as `unreviewed`
- outreach drafts start as `accepted` unless user edits or flags them

## Revision Model

The user should be able to revise artifacts without restarting the full run.

### Revision Rules

- revising the resume should not invalidate the job brief
- revising the cover letter should not delete the tailored resume
- revising outreach should not rerun resume or cover letter
- a focused retry should create a new artifact version within the same run

### Revision State Impact

- if a core artifact enters regeneration, run-level state returns to `running`
- if an optional artifact enters regeneration, run-level state may stay `needs_review` with a visible inline step status

## Human Review Triggers

Set `needs_review` when:

- a required artifact is first generated
- evidence confidence is below threshold
- the run includes unsupported or ambiguous claims
- the user requested a revision

Do not force a blocking review step for:

- job brief confirmation on high-confidence extraction
- outreach drafts when the user only wants application docs

## UX Rules For Status Presentation

- Show one run-level status badge prominently.
- Show step-level detail only as supporting context.
- Use plain-language labels, not internal workflow names.
- Preserve completed artifacts on partial failure.
- Every failed step must offer a next action: retry, edit input, or continue without it.

## Backend Contract Requirements

- Run state must be durable and queryable after page refresh.
- Step state must include timestamps and latest message.
- Terminal states must be explicit: `ready`, `partial`, `failed`, `canceled`, `archived`.
- Artifact versioning must survive retries and revisions.
- The frontend should never infer completion solely from missing active steps.
