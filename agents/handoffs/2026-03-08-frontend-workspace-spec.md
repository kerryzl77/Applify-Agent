# Frontend Handoff - 2026-03-08

Added a repo-grounded workspace unification spec at `agents/specs/applify-workspace-unification.md`.

What it covers:

- page flow spec for first-time, active-run, artifact-review, and Gmail delivery states
- component map for a unified workspace shell
- design debt list tied to the current `Dashboard`, `DiscoverJobs`, `Campaign`, `Sidebar`, and generator architecture
- phased implementation plan for merging dashboard and campaign experiences

Recommended next execution order:

- PM reviews naming and acceptance criteria
- Full-stack confirms run/artifact contract shape
- Frontend implements new `Workspace` route and migrates existing pieces into it
