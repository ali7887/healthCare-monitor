# Deployment (Local & Demo)

## Goal
Reliable, reproducible local and demo setup for portfolio/interview use. The
default path needs **no Docker, no Postgres, and no API key**. Production
hardening (TLS, managed Postgres, secrets management, scaling) is intentionally
out of scope for this MVP.

## Stack
- Frontend: Next.js 15 (`caretrace/frontend`)
- Backend: FastAPI (`caretrace/backend`)
- Database: SQLite by default (local file); Postgres optional and supported

## Environment variables

**Backend** (`caretrace/backend/.env`; every value has a working default):
- `DATABASE_URL` — defaults to `sqlite:///./caretrace_demo.db`
- `CORS_ORIGINS` — comma-separated allowed browser origins (default `http://localhost:3000`)
- `DEFAULT_PROVIDER` / `DEFAULT_MODEL` — `openai`/`gpt-4o-mini` by default
- `OPENAI_API_KEY` — only needed for live extraction (not for the seeded demo)
- `OLLAMA_BASE_URL` / `OLLAMA_MODEL` — optional local provider

**Frontend** (`caretrace/frontend/.env.local`):
- `NEXT_PUBLIC_API_BASE_URL` — e.g. `http://localhost:8000/api`

## Local startup (SQLite demo — the default path)

### Backend
```bash
cd caretrace/backend
cp .env.example .env             # optional; defaults work as-is
uv sync
uv run python -m app.seed_demo   # create tables + load demo dataset
uv run uvicorn app.main:app --reload --port 8000
```
Tables auto-create on startup when using SQLite, so seeding is the only data step.

### Frontend
```bash
cd caretrace/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### Verify
- Backend health: <http://localhost:8000/api/health> → `{"status":"ok","service":"healthCare-monitor-backend"}`
- Frontend: <http://localhost:3000/dashboard> (header pill shows **API online**)

## Demo data
```bash
uv run python -m app.seed_demo        # reset to the known demo dataset
uv run python -m app.seed_demo --keep # append without clearing
```
The dataset spans every routing path (auto-save, needs-review, reviewed incl. an
edited approval, rejected, failed) across the last two weeks so the charts render
a natural distribution. Counts are modest and honest — a demo dataset, not
synthetic production traffic.

## Using Postgres instead (optional, production-like)
```bash
# 1. Point at your Postgres instance
export DATABASE_URL='postgresql+psycopg://healthcare:healthcare@localhost:5432/healthcare'
# 2. Create the schema with Alembic (no auto-create on Postgres)
uv run alembic upgrade head
# 3. (optional) seed
uv run python -m app.seed_demo
```
The models are dialect-portable (VARCHAR+CHECK enums, generic Uuid/JSON,
Python-side defaults), so no code changes are required.

## Optional local LLM provider (Ollama)
```bash
ollama pull qwen2.5
ollama serve
```
Set `OLLAMA_BASE_URL` and select the `ollama` provider when processing a
transcript. Not required for the seeded demo or the dashboard.

## Recovery
- **Charts empty / odd** → re-run `uv run python -m app.seed_demo`.
- **CORS errors in the browser** → add your origin to `CORS_ORIGINS`.
- **API unreachable** → confirm the backend runs on `:8000` and
  `NEXT_PUBLIC_API_BASE_URL` matches.
- **Fresh start** → delete `caretrace/backend/caretrace_demo.db` and re-seed.

## Migrations
- SQLite (demo): tables auto-create on startup; no migration step needed.
- Postgres: managed by Alembic; keep a single linear history and prefer additive
  changes to preserve trace tables.
