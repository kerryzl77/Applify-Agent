# North-Star Workflow

## Product Intent

Applify should feel like one premium application agent that turns a job posting into the best application package for that job. The product should not present resume tailoring, cover letter generation, and outreach as separate tools. Those are outputs of a single application run.

The primary user promise is:

`Paste a job URL and get the best application package for this job.`

For an early-career or new-grad user, the product should reduce ambiguity at every step:

- what Applify needs from them
- what Applify is doing now
- what is ready to review
- what still needs human judgment

## Current Journey Audit

The current repo expresses three fragmented product modes:

1. `Discover Jobs` is a sourcing surface.
2. `Dashboard` is a standalone content generator driven by content type conversations.
3. `Campaign` is a separate outreach workflow launched after saving a job.

This causes product-level fragmentation:

- The user chooses a tool before choosing the job outcome.
- Resume, cover letter, and outreach are generated in different places with different mental models.
- The job URL is not consistently treated as the primary entry point.
- The main CTA changes by screen: upload resume, generate content, refresh jobs, start campaign.
- Trust is reduced because the user cannot clearly tell whether outputs share the same job understanding and candidate evidence.

## North-Star Product Model

The core product object is the `application_run`.

An application run is the durable record for:

- source job
- normalized job brief
- candidate evidence snapshot
- generation state
- output artifacts
- review decisions
- outreach readiness

Every major user-visible artifact should attach to one application run:

- tailored resume
- cover letter
- job brief
- application notes / evidence summary
- cold outreach drafts

## North-Star Workflow

### 1. Ingest Job

Primary entry:

- user pastes a job URL

Secondary entry:

- user selects a discovered job from the feed

System behavior:

- extract and normalize the posting
- generate a concise job brief
- highlight role, company, location, seniority, top requirements, and likely missing signals

### 2. Confirm Readiness

Before launch, the user sees a lightweight preflight card:

- job looks correct
- resume/profile is available
- optional warning if candidate profile is thin

The screen should not ask the user to configure templates, tone presets, or workflow modes.

Primary CTA:

- `Create best application package`

### 3. Run Package

Applify launches one asynchronous application run that executes in a fixed order:

1. normalize and score the job
2. retrieve candidate evidence
3. tailor resume
4. generate cover letter
5. generate outreach drafts
6. package artifacts for review/export

The run must feel like one system process, not a queue of unrelated tools.

### 4. Review Package

The user lands on a single application workspace with:

- run progress or completion state
- tailored resume as the primary artifact
- cover letter second
- outreach drafts third
- evidence / reasoning panel for trust

This workspace replaces the current split between dashboard and campaign.

### 5. Make Lightweight Edits Or Accept

Human review should be targeted, not mandatory everywhere:

- resume: recommended review
- cover letter: recommended review
- outreach drafts: optional quick review

The user can:

- accept artifacts as-is
- regenerate one artifact
- request a focused revision
- export the package

### 6. Use Outreach When Valuable

Outreach is downstream of the package, not a separate product mode.

The user can optionally:

- create recruiter email draft
- create hiring manager email draft
- create LinkedIn note

If they skip outreach, the application run still feels complete.

## Human Review Policy

### Review Is Useful

- Resume final pass for factual correctness, emphasis, and role fit
- Cover letter final pass for tone and any company-specific nuance
- Outreach recipient selection if the system later adds contact discovery
- Any artifact with missing or weak evidence flags

### Review Is Usually Unnecessary

- Approving the normalized job brief before run start unless extraction confidence is low
- Manually choosing workflow modes like `research_only` or `draft_only`
- Configuring output style before first run
- Stepping through every intermediate agent stage

Default principle:

- ask for human review at artifact boundaries, not system boundaries

## Screen Hierarchy

The ideal signed-in hierarchy is:

1. Home / New Application
2. Job Intake
3. Application Workspace
4. Artifact Detail
5. Profile / Resume

Notably absent:

- standalone conversation generator home
- separate campaign product area
- settings-heavy template management

## Best-In-Class Benchmark Principles

Conceptually, the product should combine:

- the clarity and speed of a premium AI assistant
- the confidence-building review model of modern tax/prep software
- the artifact quality expectations of a polished document SaaS

It should avoid:

- chat-first ambiguity
- growth-tool / CRM complexity
- expert-mode setup before first value

## Scope For Seed-Stage Heroku

In scope now:

- one job URL intake flow
- one durable application run
- one review workspace
- exportable resume and cover letter
- basic outreach drafts attached to the same run
- step-level status, retry, and persistence

Out of scope now:

- template marketplace
- multi-step onboarding wizard
- advanced style controls
- team collaboration
- full CRM/contact pipeline
- highly configurable campaign automation

## Product Acceptance Criteria

- A new user can start from a job URL without choosing among disconnected tools.
- The primary CTA always maps to creating an application package, not a single artifact.
- Resume tailoring is visually and functionally the lead artifact in the workspace.
- Cover letter generation is included by default in the same run.
- Outreach drafts are available from the same run without requiring a mode switch.
- The user can understand the run state and package readiness from one screen.
- The app can be explained in one sentence: `Applify creates the best application package for a job from a single job link.`
