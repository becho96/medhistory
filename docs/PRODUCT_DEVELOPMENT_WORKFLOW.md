# MedHistory Product Development Workflow

GitHub Issues are the source of truth for the quick-start MedHistory workflow. Hermes is the main intake window: Boris can send a Telegram voice/text message, Hermes turns it into an issue, asks only necessary clarifying questions, and runs the task through research, specification, implementation, testing, and deployment gates.

## Principles

- Boris owns product/business decisions.
- Hermes may automate triage, research, specs, implementation plans, coding, tests, PRs, and status updates.
- Product decisions, medical/legal wording, auth, PII, migrations, prod config, nginx, GitHub Actions, and production deploy require explicit confirmation.
- Every material change should be traceable from GitHub issue → branch/commit/PR → tests → deploy note.
- UI, medical terminology, and LLM-facing product copy are in Russian. Code and commits are in English.

## Issue types

Use the GitHub issue forms in `.github/ISSUE_TEMPLATE/`:

- **Product task / feature** — product ideas, UX, new capabilities.
- **Bug report** — broken or incorrect behavior.
- **Growth / acquisition task** — activation, landing, analytics, channels, positioning.
- **Research / decision memo** — questions that need analysis before implementation.

## Labels

Core labels:

- `needs-triage` — new intake, not yet clarified.
- `needs-boris` — blocked on Boris's product/business decision.
- `ready-for-dev` — spec is accepted and implementation can start.
- `in-progress` — implementation/research is running.
- `ready-for-review` — implementation complete, needs review/checks.
- `ready-for-deploy` — merged/ready but production deploy not yet approved or run.
- `deployed` — production deployment completed.

Domain labels:

- `product`, `growth`, `research`, `frontend`, `backend`, `ai`, `infra`, `legal`, `analytics`, `auth`, `pii`, `medical-safety`.

Priority labels:

- `priority:high`, `priority:medium`, `priority:low`.

## Standard lifecycle

1. **Intake**
   - Capture Boris's idea/request in an issue.
   - Add `needs-triage` and relevant domain labels.
   - Ask clarifying questions only if they affect the task definition or product decision.

2. **Triage**
   - Convert the raw request into problem, goal, non-goals, and acceptance criteria.
   - If the task requires a product choice, add `needs-boris` and stop until confirmed.
   - If the task is obvious and low-risk, move to `ready-for-dev`.

3. **Research / Spec**
   - For uncertain product/AI/growth/legal tasks, create or use a research issue first.
   - Produce options, trade-offs, and recommendation.
   - Boris confirms product/business decisions.

4. **Implementation plan**
   - Identify exact files likely to change.
   - State test/build commands.
   - Call out risky areas and deployment requirements.
   - Link implementation branch/PR back to the issue.

5. **Development**
   - Create branch from clean `main`.
   - Make surgical changes only.
   - Commit in English with conventional commits.
   - Update the issue execution log.

6. **Testing / review**
   - Frontend changes: run `npm run build` or `npx tsc --noEmit` before marking ready.
   - UI changes: verify locally on dev build, not production.
   - Backend changes: run targeted tests where available.
   - Document analysis changes: consider `benchmarks/document_analysis/`.
   - Never log PII or medical document contents; use IDs only.

7. **Deploy**
   - Production deploy requires Boris's confirmation unless the task class has been explicitly pre-approved.
   - Use GitHub Actions workflow dispatch; do not manually edit prod env/config.
   - Record workflow run URL, conclusion, and deployed ref in the issue.

8. **Close**
   - Summarize result, tests, PR/commit, deploy status, and follow-ups.
   - Close the issue only after acceptance criteria are met or explicitly marked not planned.

## Hermes intake prompt pattern

When Boris sends a new task through Telegram, Hermes should produce or update a GitHub issue with:

```markdown
## Context
<source and raw intent>

## Problem
<what user/business problem exists>

## Goal
<desired outcome>

## Non-goals
<what is out of scope now>

## Acceptance criteria
- [ ] ...

## Product decisions needed from Boris
<only decisions that matter>

## Technical notes
<known relevant MedHistory paths, APIs, risks>

## Execution log
- Intake: <date/source>
```

## Approval gates

Always ask Boris before:

- changing auth/login/session behavior;
- adding or modifying database migrations;
- changing medical interpretation prompts or user-facing medical wording;
- changing legal documents, consent flow, privacy-related copy;
- editing `.env.production`, nginx, GitHub Actions, or deployment scripts;
- deploying to production;
- sending any external communication to users, doctors, partners, or recruiters.

## Quick commands

```bash
# Create an issue from repo root
gh issue create --title "[Product] ..." --body-file /tmp/issue.md --label "product,needs-triage"

# Start implementation from an issue
gh issue develop <number> --checkout

# Create PR linked to issue
gh pr create --title "feat: ..." --body "Closes #<number>\n\n## Summary\n- ...\n\n## Test Plan\n- [ ] ..."

# Inspect deploy workflow before running it
gh workflow list --all
gh workflow view deploy.yml --yaml
```
