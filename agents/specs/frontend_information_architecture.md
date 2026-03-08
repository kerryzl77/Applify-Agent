# Frontend Information Architecture

## Goal

Define a frontend structure that makes Applify feel like one premium application agent. The IA should collapse the current split across dashboard, job discovery, and campaigns into one primary flow centered on application runs.

## IA Principles

- One primary CTA: `Create best application package`
- Job URL ingestion is the clearest way to start
- Resume tailoring is the hero artifact
- Secondary artifacts live inside the same workspace
- Users should always know what step they are in and what Applify is doing
- Avoid tool-picking, chat-picking, or settings-picking before value

## Current IA Problems

The repo currently exposes:

- `/dashboard` for chat-like content generation
- `/discover` for jobs feed
- `/campaigns/:id` for outreach workflow

This IA teaches the user that Applify is multiple products:

- a generator
- a jobs browser
- a campaign tool

The replacement IA should teach one model:

- start with a job
- generate one package
- review and export artifacts
- optionally use outreach

## Proposed Top-Level Navigation

### Primary Nav

1. `New Application`
2. `Applications`
3. `Profile`

### Optional Secondary Entry

- `Discover Jobs`

`Discover Jobs` should exist as a feeder into `New Application`, not as a sibling product with its own long-term center of gravity.

## Screen Hierarchy

### 1. New Application

Path suggestion:

- `/`
- or `/applications/new`

Purpose:

- default landing page after sign-in
- fastest path from job URL to package run

Primary modules:

- job URL input
- recent pasted jobs or recent applications
- lightweight resume/profile readiness indicator
- optional shortcut into discovered jobs

Primary CTA:

- `Create best application package`

### 2. Job Intake Review

Path suggestion:

- `/applications/new/review`
- or `/applications/:id/draft`

Purpose:

- confirm the normalized job brief
- show any missing readiness items
- launch the run

Modules:

- normalized job summary
- top requirements
- candidate readiness card
- launch CTA

This screen should be lightweight. It is not a configuration wizard.

### 3. Application Workspace

Path suggestion:

- `/applications/:runId`

Purpose:

- single source of truth for run status, artifacts, and review

Layout priority:

1. run header
2. resume panel
3. cover letter panel
4. outreach panel
5. evidence / job brief side panel

Key elements:

- prominent run status
- artifact tabs or stacked sections
- export actions
- revise/regenerate actions
- latest accepted version indicator

This screen replaces the practical need for the current dashboard and campaign page split.

### 4. Artifact Detail

Path suggestion:

- `/applications/:runId/resume`
- `/applications/:runId/cover-letter`
- `/applications/:runId/outreach/:type`

Purpose:

- focused reading, editing, and version review for one artifact

Use when:

- the user wants full-screen review
- the artifact needs revision
- the user is comparing versions

### 5. Applications Index

Path suggestion:

- `/applications`

Purpose:

- list prior application runs
- allow resume of work
- make persistence visible

List items should show:

- company
- role
- run status
- last updated
- package completeness

### 6. Profile

Path suggestion:

- `/profile`

Purpose:

- manage resume and core candidate information

Modules:

- current resume/profile snapshot
- upload / replace resume
- extracted profile preview

This is supporting infrastructure, not the product center.

## Discover Jobs Placement

Discover Jobs should be reframed as optional sourcing support.

Rules:

- accessible from top nav or a secondary tab
- selecting a job should route into job intake review or directly create a draft application run
- no separate `start campaign` CTA from the jobs drawer
- the main action on a job should become `Create application package`

## Application Workspace Structure

### Header

- company + role
- run status badge
- updated timestamp
- primary export action
- secondary regenerate action

### Main Column

- resume section
- cover letter section
- outreach section

### Side Panel

- job brief
- top requirements
- evidence confidence / source notes
- review guidance

This gives the product a premium, confident feel: one calm workspace, not a set of scattered drawers and tool screens.

## CTA Hierarchy

### Global Primary CTA

- `Create best application package`

### Secondary CTAs

- `Review resume`
- `Review cover letter`
- `Use outreach draft`
- `Retry failed step`

### CTAs To Remove Or Demote

- `New Cover Letter`
- `New Connection Email`
- `New Hiring Manager Email`
- `New LinkedIn Message`
- `Tailor Resume`
- `Start Campaign`

Those actions can still exist internally as artifact-specific operations, but not as top-level product entry points.

## Sidebar / Nav Migration Guidance

Replace the current sidebar model of content-type creation and recent conversations with:

- `New Application`
- `Applications`
- `Discover Jobs`
- `Profile`

Recent activity should show recent application runs, not recent conversation threads.

## Mobile Behavior

- Job URL input remains above the fold.
- Application workspace defaults to artifact tabs instead of dense multi-column layout.
- Export and regenerate actions stay sticky or easy to access.
- Side-panel content becomes drawers or accordions.

## Acceptance Criteria

- A signed-in user lands on a page that asks for a job, not a content type.
- A job selected from discovery feeds directly into package creation.
- Resume, cover letter, and outreach are reachable from one run workspace.
- The navigation does not present campaigning as a separate product area.
- Recent history is organized around application runs, not chats.
- The product can be understood from the nav alone as one application agent.
