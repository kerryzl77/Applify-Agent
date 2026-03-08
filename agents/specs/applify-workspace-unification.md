# Applify Workspace Unification Spec

## Objective

Make Applify feel like one premium application workspace centered on a single primary action:

- paste a job URL
- generate the best tailored package
- review artifacts and outreach in the same place

The product should no longer read as three separate tools (`Dashboard`, `Discover Jobs`, `Campaigns`). It should behave like one continuous workspace with one active job context and one active package run.

## UX Principles

- One workspace, one job context, one package state
- Primary action above navigation: paste job URL and generate package
- Progressive disclosure over separate modes and pages
- Artifact review before outreach actions
- Gmail connection treated as an inline capability, not a side quest
- Calm hierarchy: fewer cards, fewer button styles, less gradient noise

## Current Journey Problems

Based on the current frontend:

- `Dashboard` is a content tool driven by local conversation types rather than job context.
- `DiscoverJobs` is a separate feed with separate top bar, filters, and job actions.
- `Campaign` is a third mental model with workflow steps, contacts, and drafts.
- `Sidebar` reinforces product split by offering `Discover Jobs` plus five separate generation actions.
- Resume upload is a top-bar utility in one page, but a blocking prerequisite for package quality everywhere.
- Gmail setup appears as a modal utility instead of a clear step in artifact delivery.
- Status language is inconsistent: `Generate`, `Start Campaign`, `Confirm`, `Create Draft`, `Refresh Jobs`.

This creates mode switching at exactly the moment a first-time user needs a simple, legible path.

## Proposed Product Model

Replace the current split with a unified `Workspace` route that owns the end-to-end flow.

### Top-level structure

- Left rail: lightweight navigation and recent jobs/runs
- Main workspace column: job intake, package generation, progress, artifact review
- Context side sheet or bottom sheet: job brief, source details, contacts, Gmail state when needed

### Primary objects

- Candidate profile
- Active job
- Application package run
- Package artifacts
- Outreach delivery state

### Route model

- `/workspace`
- `/workspace/job/:jobId`
- `/workspace/job/:jobId/run/:runId`

Keep legacy routes temporarily, but redirect their successful end states into the workspace.

## Page Flow Spec

### 1. First-time entry

The first screen should answer three questions in under 30 seconds:

- What is this? `Generate a tailored application package from a job URL`
- What do I do first? `Upload resume` if missing, then `Paste job URL`
- What do I get? `Resume, cover letter, evidence, and outreach drafts`

#### First-time layout

- Hero input anchored near the top: job URL field plus primary CTA `Generate package`
- Compact resume status chip beside or above the CTA
- One supporting line describing outputs
- Optional secondary action: `Browse saved jobs`

If no resume exists:

- Keep the URL field visible
- Disable package generation with a clear inline blocker card: `Upload resume to personalize outputs`
- Use inline uploader or drawer, not a separate modal-first flow

### 2. Job intake

User pastes a URL or selects a saved/discovered job.

System response:

- Extract job
- Show normalized job brief in place
- Auto-save the job to the workspace list
- Present a single next step: `Generate package`

Normalized job brief should include:

- role title
- company
- location/team
- top requirements summary
- source link
- confidence or extraction status if parsing is partial

### 3. Package generation

On `Generate package`, create one run and transition the workspace into run mode without a route jump feeling.

Progress UI should be one compact vertical timeline with 4 steps:

1. Analyze job
2. Tailor resume
3. Draft application materials
4. Prepare outreach

Each step shows:

- current status
- short system message
- expandable details only when useful

Do not expose low-level agent traces by default. Trace output can live under `View details`.

### 4. Artifact review

When steps complete, the workspace should shift from progress-first to artifact-first.

Artifact area should show strong tabs or segmented controls for:

- Resume
- Cover Letter
- Outreach
- Evidence

Review behavior:

- preview first
- export/download second
- regenerate/refine as a scoped action

Each artifact panel should support:

- summary header
- preview content
- `Refine` action
- `Download` action where relevant
- status badge tied to the current run

### 5. Outreach review and contacts

Contacts should no longer feel like a separate campaign product. They belong inside outreach review.

Outreach panel structure:

- recommended contacts
- selected delivery targets
- draft variants
- Gmail delivery state

If the system needs user input:

- freeze the run into `Needs review`
- highlight the exact decision needed
- keep the user in the same artifact surface

### 6. Gmail connect and save draft

Gmail is a delivery capability inside outreach, not a setup destination.

States:

- Not configured: show admin/system issue plainly
- Configured but disconnected: `Connect Gmail to save drafts`
- Connected: show connected account state and `Save drafts to Gmail`
- Saving: inline progress, no modal interruption
- Saved: success state with draft count and next step

The connect CTA should live adjacent to outreach drafts, not hidden behind a generic modal button.

### 7. Returning user flow

Returning users should land on the same workspace with:

- recent jobs/runs in the rail
- the latest active job/run reopened in the main pane
- the hero intake still available in compact form

The workspace should always preserve the sense that generating a new package and reviewing an old one are variations of the same activity.

## Component Map

### Shell

- `WorkspaceShell`
- `WorkspaceRail`
- `WorkspaceHeader`
- `WorkspaceContextPanel`

### Intake

- `JobIntakeHero`
- `ResumeStatusCard`
- `InlineResumeUploader`
- `JobSourceInput`
- `RecentJobsList`

### Job review

- `JobBriefCard`
- `JobRequirementList`
- `ExtractionStatusBadge`
- `SourceLinkRow`

### Run and progress

- `PackageRunHeader`
- `PackageProgressTimeline`
- `ProgressStepCard`
- `RunStateBanner`

### Artifact review

- `ArtifactTabs`
- `ArtifactPreviewPane`
- `ResumePreviewCard`
- `CoverLetterPreviewCard`
- `EvidencePanel`
- `ArtifactActionBar`

### Outreach

- `OutreachPanel`
- `ContactRecommendations`
- `ContactSelectCard`
- `DraftVariantTabs`
- `DraftPreview`
- `FeedbackComposer`
- `DeliveryActionBar`

### Gmail

- `GmailConnectionBanner`
- `GmailConnectionSheet`
- `DraftSaveStatus`

### Shared states

- `EmptyWorkspaceState`
- `MissingResumeState`
- `RunInProgressState`
- `NeedsReviewState`
- `ArtifactReadyState`
- `InlineErrorState`

## Screen Architecture

### Desktop

- Left rail fixed at narrow width
- Main column centered and dominant
- Right context panel optional and collapsible

Preferred pattern:

- rail for navigation/history
- single main narrative column
- one supplemental panel only when needed

Avoid permanent three-pane density.

### Mobile

- stacked flow
- sticky primary CTA/footer actions
- context panel becomes bottom sheet
- recent jobs move into a drawer or sheet

## Primary Action Hierarchy

The UI should consistently prioritize:

1. `Paste job URL`
2. `Generate package`
3. `Review artifacts`
4. `Save Gmail drafts`

Everything else is secondary:

- discover jobs
- manual content generation variants
- raw traces
- advanced settings

## Design Debt List

### Structural debt

- Separate routes encode separate product identities instead of one workflow.
- Local `conversations` state in Zustand models content generation as chat sessions rather than package runs.
- Job discovery and campaign execution are disconnected from the main generator state.

### IA debt

- Sidebar offers too many creation choices for a first-time user.
- Primary CTA changes by screen, so the product does not teach one default action.
- Resume upload, profile, Gmail, and job extraction are framed as utilities rather than core flow prerequisites.

### Interaction debt

- `Start Campaign` is unclear compared with the desired user outcome.
- Contact selection and Gmail draft creation happen too late and in a different mental model.
- Progress surfaces expose system mechanics more than user-relevant milestones.

### Visual debt

- Multiple gradient treatments compete for attention across sidebar, banners, and action areas.
- Top bars differ across pages, which fragments hierarchy.
- Card density is high and many cards have equal visual weight.
- Button styles and status badges do not form one consistent action system.

### Content debt

- Language alternates between content generation, campaigns, jobs, and drafts.
- Workflow statuses are implementation-driven rather than outcome-driven.
- Empty states teach feature usage instead of guiding the main package flow.

## Implementation Plan

### Phase 1: Unify information architecture

- Introduce a new `Workspace` page as the default authenticated route.
- Reframe `Sidebar` into a lightweight rail focused on recent jobs/runs and profile access.
- Remove separate quick-create content actions from primary navigation.
- Add one intake hero for job URL plus resume state.

### Phase 2: Merge job intake and generation

- Move job URL extraction from `DiscoverJobs` into the workspace hero.
- Reuse job feed/saved jobs as a secondary picker inside the workspace.
- Convert `JobDetailDrawer` into a job brief/context panel that feeds package generation.
- Replace `Start Campaign` with `Generate package`.

### Phase 3: Replace conversation model with package model in UI

- Stop centering the UI on local conversation types.
- Introduce client state for active job, active run, and package artifacts.
- Map existing campaign status/events into the workspace progress timeline.
- Keep manual single-artifact generation only as a secondary refine action inside artifact tabs.

### Phase 4: Merge campaign review into artifact workspace

- Fold `Campaign` contacts, drafts, and progress sections into the unified run view.
- Rename workflow steps to user-facing package milestones.
- Hide trace details behind disclosure instead of leading with them.

### Phase 5: Integrate Gmail as inline delivery

- Replace generic `GmailSetup` modal-first flow with inline connection banners and sheets.
- Keep connect/disconnect logic, but surface it only inside outreach delivery moments.
- Add clear post-save success states tied to selected drafts.

### Phase 6: Polish and harden

- Normalize top bar, spacing, button hierarchy, and status treatments.
- Reduce gradients to one restrained brand accent system.
- Audit empty, loading, waiting, and error states for a single voice.
- Add motion only where it reinforces step transitions and saved-state confidence.

## Suggested Component Migration

### Reuse with adaptation

- `ResumeUploader` -> inline uploader within workspace
- `JobDetailDrawer` -> context panel / job brief panel
- `Campaign` step logic -> package progress timeline
- `Campaign` draft/contact logic -> outreach panel
- `GmailSetup` logic -> inline Gmail connection components

### De-emphasize or retire

- `Dashboard`
- route-first `DiscoverJobs`
- route-first `Campaign`
- quick-create content buttons in `Sidebar`
- local conversation-centric empty state in `ContentGenerator`

## Acceptance Criteria For The Merge

- A first-time user can identify `Paste job URL` as the primary action within 5 seconds.
- A first-time user can understand that resume upload is required before generation without opening multiple screens.
- Generating a package never requires a route jump that feels like entering a different product.
- Progress, artifacts, contacts, and Gmail delivery all appear within one workspace context.
- Saved jobs and previous runs are accessible without displacing the main generation surface.
- The language `package`, `artifacts`, `review`, and `save drafts` replaces ambiguous campaign/tool terminology.

## Engineering Notes

- Current frontend code is already close to reusable pieces; the main issue is composition, naming, and route boundaries.
- The largest frontend state change is moving from `conversationId` to `jobId/runId/artifacts`.
- Backend contracts should ideally expose one canonical package run object with:
  - `job`
  - `run`
  - `steps`
  - `artifacts`
  - `contacts`
  - `delivery`
- Legacy pages can remain as compatibility routes while progressively redirecting into the workspace.
