# healthCare-monitor

**Reliable handling of AI-generated clinical documentation — with deterministic validation, full traceability, and human review.**

healthCare-monitor turns unstructured nursing/caregiver transcripts into structured clinical notes, then treats the model's output as *untrusted* until it has passed deterministic checks. Every run is scored, routed, and stored as a complete audit trace. Low-confidence or clinically inconsistent outputs are flagged for a human instead of being silently saved.

> This is a robust, demo-ready MVP built to showcase reliability engineering around LLM output — not a certified medical device. It does **not** diagnose, prescribe, or recommend treatment; it structures documentation and surfaces *potential inconsistencies* for human review.

---

## Why this project is interesting

Naive "call the LLM and store the JSON" pipelines fail exactly where healthcare can't afford it: malformed output, missing fields, clinically implausible values, and no way to explain *why* a result was trusted. This project is a study in making an LLM feature **operationally credible**:

- **Deterministic validation over model self-trust.** The model is never asked how confident it is. Confidence is *derived locally* from concrete validation outcomes.
- **Traceability by default.** Every run persists its raw response, parsed output, validation issues, routing decision, and the confidence breakdown that produced it.
- **Human-in-the-loop as a first-class path**, including *edited approvals* where a reviewer's correction is stored without ever overwriting the original model output.
- **Tested and hardened**: 86 backend tests + 25 frontend tests, per-widget error boundaries, an immutable-decision conflict guard, and a lazy-loaded chart layer.

See [`docs/ENGINEERING_DECISIONS.md`](docs/ENGINEERING_DECISIONS.md) for the tradeoffs behind each of these.

---

## What it does — the processing flow

```
transcript
   │
   ▼
1. AI extraction (OpenAI GPT-4o-mini or local Ollama)   ── provider abstraction
2. schema validation           (Pydantic v2)
3. clinical validation         (deterministic rule engine, local)
4. retry once if validation failed  (bounded self-correction)
5. derived confidence score    (base 1.0 − capped penalties, clamped [0,1])
6. routing decision:
       ≥ 0.85 & no critical issue  → auto-save
       0.50–0.84 or any critical   → human review
       < 0.50                      → reject
7. persist the complete trace (run + issues + review item)
   │
   ▼
dashboard · runs table · trace viewer · review queue
```

Statuses: `auto_saved` · `needs_review` · `reviewed` · `rejected` · `failed`.

---

## Stack

| Layer | Technology |
|------|------------|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, shadcn-style UI, TanStack Query v5, Recharts (lazy-loaded) |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | SQLite by default (zero-infra demo); Postgres-ready (dialect-portable models) |
| AI orchestration | Provider abstraction over OpenAI GPT-4o-mini and local Ollama (Qwen2.5), versioned file-based prompts |
| Tooling | `uv` (Python), pytest, Vitest + React Testing Library |

---

## Architecture at a glance

- **Pure compute core, persistence at the edge.** The pipeline, validation, confidence, and routing services are pure functions with no ORM imports; persistence happens only at the API boundary. This keeps the reliability logic unit-testable and free of database/import cycles.
- **Stable typed contracts.** Backend Pydantic read-models map 1:1 to frontend TypeScript types (e.g. `RunDetail`, `DashboardStats`, `DashboardTimeseries`).
- **Portable persistence.** Enums are stored as `VARCHAR + CHECK` (not native Postgres enums), UUID/JSON use generic types, and timestamps use Python-side defaults — so the exact same models run on SQLite and Postgres.
- **Observable dashboard.** KPI strip, routing-distribution donut, and a real per-day throughput trend, all sharing one `ROUTING_SERIES` config so the donut and trend can never drift out of alignment.

More detail: [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`docs/AI_PIPELINE.md`](docs/AI_PIPELINE.md) · [`docs/API.md`](docs/API.md).

---

## Run it locally

From a clean checkout you can be looking at a populated dashboard in a few minutes — **no Docker, no Postgres, no API key required** (the seeded demo needs none of them).

**Prerequisites:** Node.js 18+, Python 3.11+, and [`uv`](https://docs.astral.sh/uv/).

### 1. Backend (terminal 1)

```bash
cd caretrace/backend
cp .env.example .env            # optional — defaults work out of the box
uv sync                         # install dependencies
uv run python -m app.seed_demo  # create tables + load the demo dataset
uv run uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health> → `{"status":"ok","service":"healthCare-monitor-backend"}`

### 2. Frontend (terminal 2)

```bash
cd caretrace/frontend
cp .env.local.example .env.local   # points at http://localhost:8000/api
npm install
npm run dev
```

Open <http://localhost:3000/dashboard>.

> **SQLite is the default.** Tables auto-create on backend startup and `seed_demo` fills them with a realistic distribution across every routing path. To use Postgres instead, set `DATABASE_URL` and run `uv run alembic upgrade head`.
>
> **Live extraction** (processing your own transcript instead of the seeded data) needs an `OPENAI_API_KEY`, or a running Ollama with `qwen2.5`. Sample transcripts live in [`examples/`](examples/).

---

## Test

```bash
# Backend — 86 tests
cd caretrace/backend && uv run pytest

# Frontend — 25 tests, types, and production build
cd caretrace/frontend
npm run test          # Vitest + React Testing Library
npx tsc --noEmit      # type check
npm run build         # production build
```

Testing priorities and coverage map: [`docs/TESTING.md`](docs/TESTING.md) and [`docs/QA_CHECKLIST.md`](docs/QA_CHECKLIST.md).

Browser E2E + screenshots (Playwright):

```bash
cd caretrace/frontend
npm run test:e2e      # demo-path + secondary flows (starts its own seeded backend)
npm run e2e:screens   # regenerate docs/screenshots/ from seeded data
```

---

## Continuous integration

A single GitHub Actions workflow ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))
enforces the quality gates on every push and pull request, running the **same
commands** used locally — no Docker, no hosted database (the backend uses the
isolated, self-seeding SQLite workflow).

| Job | What it runs | Blocking |
|-----|--------------|----------|
| **Frontend** | `npm run ci:frontend` → type-check + Vitest unit tests + production build | ✅ |
| **Backend** | `uv run pytest` | ✅ |
| **E2E** | `npm run ci:e2e` — Playwright drives an isolated seeded backend + production frontend (runs only after the fast gates pass) | ✅ |
| **Screenshots** | `npm run e2e:screens`, uploaded as an artifact (main / manual only, to keep PRs fast) | ⬜ non-blocking |

- **Run the same checks locally:** `npm run ci:frontend`, `uv run pytest`, `npm run test:e2e`.
- **Browser caveat:** CI installs the real Chrome channel (`npx playwright install --with-deps chrome`), matching the local `channel: "chrome"` config (chosen because the Playwright browser CDN is geo-blocked on the primary dev machine).
- **Artifacts:** the Playwright HTML report (always) and failure traces (on failure) are uploaded per run; the screenshots job publishes the demo PNGs. Retention is 7–14 days.

---

## Demo walkthrough

A full script — happy path, review/approve/reject, edited approval, reading the dashboard, and recovery steps — is in [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md). The short version:

1. **Dashboard** — KPI strip + routing donut + throughput trend, populated by the seed.
2. **Runs table** — filter by routing decision; open any run.
3. **Trace viewer** — inspect a run's transcript, structured output, validation issues, and confidence breakdown.
4. **Review queue** — open a `needs_review` run, optionally **edit** the output, then approve or reject; watch the dashboard update via cache invalidation.

Reset to a clean demo state at any time:

```bash
cd caretrace/backend && uv run python -m app.seed_demo
```

---

## Scope

Intentionally excluded to keep the MVP focused: authentication, RBAC, multi-tenancy, voice/audio streaming, RAG / vector search, real EHR integration, notifications, realtime collaboration, billing, and any diagnosis/treatment functionality.

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — project constraints and working rules
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, pipeline, entities
- [`DECISIONS.md`](DECISIONS.md) · [`docs/ENGINEERING_DECISIONS.md`](docs/ENGINEERING_DECISIONS.md) — design rationale
- [`docs/API.md`](docs/API.md) — HTTP contracts
- [`docs/AI_PIPELINE.md`](docs/AI_PIPELINE.md) — end-to-end processing pipeline
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — local/demo setup
- [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) — presentation script
- [`docs/TESTING.md`](docs/TESTING.md) · [`docs/QA_CHECKLIST.md`](docs/QA_CHECKLIST.md) — testing strategy & QA
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) — clinical-calm design system
