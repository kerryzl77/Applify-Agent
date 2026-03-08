# Document Intelligence Quality Bar

## Goal

Define the shared contract and review standard for resume extraction, job understanding, resume tailoring, cover letters, and outreach.

This spec assumes:

- the uploaded resume is the source of truth
- every generated artifact must be grounded in candidate evidence and job requirements
- the default resume output is one polished ATS-safe PDF
- cover letters and outreach are concise by default

## Canonical Candidate Profile Schema

Code contract: `app/document_intelligence_models.py`

### Principles

- Preserve source truth: extracted facts come from the uploaded resume unless explicitly user-edited.
- Track provenance on normalized fields and generated evidence links.
- Store candidate facts in reusable units that can be ranked, elevated, condensed, or excluded.
- Keep a stable item ID on experiences, bullets, projects, education, and stories so downstream artifacts can cite them.

### Required profile sections

- `contact`: normalized contact and links
- `headline` and `summary`: short recruiter-facing framing, still grounded in resume evidence
- `core_skills`: normalized skills with evidence references
- `experience`: role-level entries with bullet-level achievement units
- `education`
- `projects`
- `story_bank`: interview/outreach-ready evidence derived from resume facts
- `preferences`: target-title/location preferences if user later edits them
- `raw_resume_text`: optional normalized text snapshot for debugging and regression review

### Provenance model

Every normalized field should be traceable through one or more `Provenance` records:

- `source_kind`: uploaded resume, parsed resume, user edit, job posting, web research, or system inference
- `locator`: a lightweight pointer such as `page_1.block_4`, `exp_2.bullet_1`, or `qualifications.section`
- `excerpt`: short supporting text
- `confidence`: parser/model confidence
- `inferred`: true only when the value is derived rather than directly stated

### Merge policy

- Resume upload replaces resume-grounded sections when the new source is stronger.
- Explicit user edits outrank parser output for the edited field only.
- System inferences never overwrite directly stated candidate facts.
- Missing fields remain blank rather than guessed.

## Job Requirement Schema

The normalized job brief should capture both raw text and structured requirements.

### Required sections

- core job metadata: title, company, location, work arrangement, employment type, seniority
- `responsibilities`
- `qualifications`
- `preferred_qualifications`
- `tech_stack`
- `domain_signals`
- `keywords`
- `normalized_summary`
- `raw_job_text`
- `fallback`

### Requirement unit

Each requirement should be a stable object with:

- `requirement_id`
- `label`
- `priority`: `must_have`, `preferred`, `nice_to_have`, or `inferred`
- `category`: technical, domain, leadership, communication, execution, etc.
- `keywords`
- `rationale`
- requirement-level evidence from the JD
- confidence

### Thin or messy JD fallback

Use `fallback` to record safe degradation behavior:

- `should_backfill`: whether lightweight research or inference is needed
- `missing_fields`: title, stack, seniority, etc.
- `assumptions`: minimal assumptions allowed for generation
- `safe_defaults`: conservative defaults such as general software-engineering framing instead of company-specific claims

Fallback rules:

- Do not invent projects, metrics, or domain expertise.
- Prefer generalized but role-relevant phrasing over specific but unsupported claims.
- If company context is thin, personalize to role and public company basics only.
- Outreach should still sound human, but it can be lighter on specificity instead of faking detail.

## Shared Grounding Model

All output types should consume the same `ApplicationEvidencePack`.

### How it works

- Normalize candidate profile
- Normalize job profile
- Build requirement coverage objects
- Select evidence links per requirement
- Generate a tailoring plan
- Generate artifacts from the plan, not directly from raw blobs

### Why this matters

- Resume, cover letter, and outreach stop disagreeing with each other
- one-page tradeoffs become explicit decisions rather than accidental truncation
- evaluation can inspect coverage gaps and unsupported claims directly

## Resume Tailoring Rubric

Score each dimension from 1 to 5.

### Relevance

- `5`: top requirements are obvious in summary, skills, and first bullets
- `3`: some relevant content is present but ordering is weak
- `1`: reads like a generic resume with little role targeting

### Evidence grounding

- `5`: every major claim maps cleanly to candidate evidence
- `3`: mostly grounded, with some vague unsupported phrasing
- `1`: inflated or unverifiable claims appear

### ATS safety

- `5`: standard headings, clear chronology, keyword use is natural, no gimmicks
- `3`: mostly safe but has awkward phrasing or inconsistent section structure
- `1`: ornate formatting, stuffed keywords, or non-standard structure

### Concision

- `5`: bullets are tight, informative, and non-redundant
- `3`: some bloat or repeated ideas
- `1`: overly long, repetitive, or mushy

### One-page fit

- `5`: fits on one page without obvious loss of the strongest evidence
- `3`: fits but with visible crowding or weak prioritization
- `1`: spills over or preserves the wrong content

### Credibility

- `5`: strong but believable; no inflated seniority or invented outcomes
- `3`: mostly believable with minor overreach
- `1`: obvious exaggeration or title inflation

### Tailoring rules

- Prioritize requirement coverage before chronology completeness.
- Prefer fewer stronger bullets over many weak bullets.
- Preserve quantified outcomes whenever they exist.
- Drop low-signal older content before cutting high-signal recent evidence.
- If a requirement is uncovered, do not fake coverage; show adjacent evidence or leave it out.

## Cover Letter Rubric

Score each dimension from 1 to 5.

### Grounding

- `5`: references the role, company, and candidate evidence precisely
- `3`: role-relevant but somewhat generic
- `1`: could be sent to any company

### Specificity

- `5`: highlights 1 to 2 concrete evidence-backed reasons for fit
- `3`: mentions relevant themes but not enough specifics
- `1`: generic motivation language dominates

### Tone

- `5`: confident, concise, credible, recruiter-friendly
- `3`: acceptable but stiff, over-eager, or too self-promotional
- `1`: ornate, needy, or inflated

### Concision

- `5`: roughly 220 to 320 words with no dead weight
- `3`: a bit long or slightly repetitive
- `1`: verbose or rambling

### Credibility

- `5`: no unsupported company flattery or invented alignment
- `3`: minor speculative phrasing
- `1`: obvious hallucination or excessive praise

### Cover letter rules

- Open with fit, not autobiography.
- Use one tight body paragraph if evidence is strong; two only when needed.
- Mention the company only when there is a real tie to role, product, mission, or operating context.
- End with interest and availability, not a dramatic call to action.

## Outreach Personalization Rubric

Score each dimension from 1 to 5.

### Personalization

- `5`: clearly tailored to recipient type and available context
- `3`: role-aware but somewhat templated
- `1`: generic networking spam

### Grounding

- `5`: asks or frames the outreach around real candidate/job evidence
- `3`: somewhat grounded but vague
- `1`: generic buzzwords or unsupported claims

### Tone

- `5`: direct, respectful, human
- `3`: a little stiff or salesy
- `1`: cringe, needy, or overly familiar

### Clarity

- `5`: clear purpose in the first sentence and a single lightweight ask
- `3`: purpose emerges late or the ask is fuzzy
- `1`: rambling or multipurpose

### Non-cringe

- `5`: no flattery theater, hustle-speak, or fake intimacy
- `3`: one awkward phrase
- `1`: multiple awkward phrases or obvious copywriting tone

### Outreach rules

- Personalize differently for recruiter, hiring manager, and warm contact.
- Default to 70 to 140 words for email and under 200 characters for LinkedIn note.
- Ask for one small next step only.
- Never pretend there is a relationship if there is none.
- Gmail integration remains draft-only.

## Lightweight Eval Set

Store fixtures in: `agents/specs/evals/document_intelligence_eval_set.json`

### Slices

- clean technical JD + clean technical resume
- messy scrape with repeated boilerplate
- thin JD with only title/team/location
- senior IC role with heavy leadership signals
- early-career candidate where projects matter more than experience
- career-switcher with adjacent evidence but partial requirement coverage
- outreach personalization with rich recipient context
- outreach personalization with almost no recipient context

### Minimum per-case assets

- candidate resume text or parsed profile snapshot
- job text or normalized job snapshot
- expected top 3 requirements
- expected top 3 evidence items
- artifact expectations
- failure modes to watch for

## Review Workflow

### Fast loop

Run on every prompt/schema/generation change:

1. Select 6 to 10 eval cases covering at least 4 slices.
2. Generate normalized candidate profile, normalized job profile, tailoring plan, resume, cover letter, and one outreach artifact when relevant.
3. Check hard gates first:
   - unsupported claims
   - ATS-unsafe structure
   - obvious keyword stuffing
   - cover letter over-length
   - outreach cringe or fake familiarity
4. Score using the three rubrics.
5. Record deltas against baseline and note regressions by slice.

### Human review template

- What are the top requirements the system chose?
- Which candidate evidence did it elevate?
- Did any claim lack support?
- Did one-page compression cut the wrong thing?
- Would a recruiter skim this faster than baseline?
- Would you actually send the cover letter and outreach draft?

### Release gate

Do not ship a prompt/schema change unless:

- no eval case introduces unsupported claims
- average resume relevance and evidence scores improve or hold
- cover letter grounding average is at least `4.0`
- outreach non-cringe average is at least `4.0`
- no slice regresses by more than 0.5 on average without an explicit decision
