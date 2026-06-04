# AGENTS.md - MedHistory

Codex project guidance. Keep this file short enough to stay useful at session start; add rules here when they prevent recurring mistakes.

## 1. Working Principles

**Think before coding.** State assumptions explicitly. If a task has several reasonable interpretations, name them instead of silently choosing. If the ambiguity is risky, stop and ask.

**Prefer simplicity.** Implement the smallest change that solves the task. Do not add extra features, abstractions, or broad error handling unless asked.

**Make surgical changes.** Touch only files required by the task. Follow existing style. Do not reformat or improve neighboring code. Remove only code made obsolete by your own change.

**Work toward verifiable goals.** For multi-step work, state a short plan with checks before editing. Convert vague requests into a concrete outcome and verification.

## 2. Project

MedHistory manages medical history data for `medhistory.ru`. Stack: FastAPI, React 18, PostgreSQL, MongoDB, MinIO. UI text, medical terminology, and LLM prompts are in Russian; code and commits are in English.

User is a Russian-speaking solo developer. Explanations should be in Russian unless the user asks otherwise.

## 3. Entry Points And Pitfalls

- Backend entry: [backend/main.py](backend/main.py), not `backend/app/main.py`.
- API router: [backend/app/api/v1/router.py](backend/app/api/v1/router.py).
- Auth deps: [backend/app/api/deps.py](backend/app/api/deps.py): `get_current_user`, `get_db`.
- Frontend entry: [frontend/src/App.tsx](frontend/src/App.tsx).
- JWT is stored in `localStorage` as `auth_token`.
- Document analysis benchmark: [benchmarks/document_analysis/](benchmarks/document_analysis/), with `run`, `score`, and `compare`.
- Telegram bot: [bot/](bot/), aiogram long-polling, separate container; backend routes live under `/api/v1/bot/*`.

## 4. Build, Run, Verify

```bash
./deploy.local              # standard local Docker run
./deploy.local --rebuild    # rebuild images
./deploy.local --update     # quick update without rebuild

cd frontend && npm run dev
cd frontend && npm run build
cd frontend && npm run lint
```

Before calling frontend work done, verify TypeScript with `cd frontend && npm run build` or `cd frontend && npx tsc --noEmit`.

For UI testing, use MCP Playwright against the local dev build at `http://localhost:5173`, not production. Test account: `becho15rus@gmail.com` / `1234567890`.

## 5. Data

- PostgreSQL stores relational data: users, documents, interpretations, `chat_*`.
- MongoDB stores `document_metadata`. Lab values: `extracted_data.lab_results`. Summary: `extracted_data.summary`. Classification: `classification.specialties`.
- MinIO stores raw uploaded files.

Migrations are raw SQL in [backend/migrations/](backend/migrations/) as `00N_*.sql`; the current latest migration is `022`. Apply with:

```bash
psql -U medhistory_user medhistory -f backend/migrations/XXX_*.sql
```

Do not introduce Alembic. Continue the numbered SQL migration pattern.

## 6. AI / LLM

- Existing production document analysis: OpenRouter -> Gemini 2.5 Flash.
- Assistant: LangGraph multi-agent using Anthropic Claude through `langchain-anthropic`.
- LLM factory: [backend/app/services/assistant/llm_factory.py](backend/app/services/assistant/llm_factory.py).
- Graph: [backend/app/services/assistant/graph.py](backend/app/services/assistant/graph.py).
- WebSocket: `WS /api/v1/assistant/ws?token=<jwt>`.
- MCP server: `python -m mcp_server.server`.

`ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY` are required in `.env.local`.

## 7. Deployment

Keep local/dev and production configuration separate, but update both when a change affects runtime configuration, services, environment variables, build args, nginx, or deployment flow.

- Local/dev: `./deploy.local`, [docker-compose.yml](docker-compose.yml), `.env.local`.
- Production: Timeweb Cloud `194.87.140.190`, static IP.
- Production deployment flow: push to `main`, then manually trigger GitHub Actions `workflow_dispatch` for [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).
- Production compose: [docker-compose.prod.yml](docker-compose.prod.yml).
- Production env: `/root/medhistory/.env.production` on the server. Do not edit `.env.production` without explicit user approval.
- Production docs: [docs/timeweb/DEPLOYMENT.md](docs/timeweb/DEPLOYMENT.md).
- SSH: `ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190`; password auth is disabled.

When the user asks to deploy to production:

```bash
git push origin main
gh workflow run deploy.yml --repo becho96/medhistory --field ref=main --field service=all
gh run list --repo becho96/medhistory --workflow=deploy.yml --limit 1
gh run watch --repo becho96/medhistory <run-id>
```

Push directly to `main`; do not create a branch unless the user explicitly asks. After deployment, check the GitHub Actions run and production health.

Current production state: DNS points to Timeweb, Let's Encrypt certificate is issued, and nginx serves HTTPS. `www.medhistory.ru` is not configured yet; it needs an A record and certificate reissue with both domains.

## 8. Conventions

- New backend endpoints go in `backend/app/api/v1/endpoints/` and must be registered in `router.py`.
- Frontend API calls should go through TanStack Query hooks in [frontend/src/services/](frontend/src/services/), not scattered `fetch` or `axios` calls in components.
- State belongs in Zustand stores under [frontend/src/stores/](frontend/src/stores/).
- Do not log PII, document contents, or numeric lab values; log IDs only.
- Registration requires two 152-FZ consents: `terms_and_privacy` and `special_category`. They are stored in `user_consents` with sha256 of the text. Legal documents live in [frontend/public/legal/](frontend/public/legal/).

## 9. Risk Boundaries

Before risky or ambiguous changes, show a plan and wait for confirmation. This includes migrations, production config, auth flow, `deploy.local`, `nginx/`, and GitHub Actions workflows.

Never modify production secrets unless the user explicitly asks.
