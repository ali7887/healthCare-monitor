# CareTrace (healthCare-monitor) — Project Status & Context Sync

Last updated: 2026-07-05  
Current phase: **Phase 22 complete**  
Overall status: **Portfolio-grade MVP complete, fully validated locally, CI-configured, ready for next product/depth phase**

---

## Executive Summary

CareTrace has progressed from a dashboard/review MVP into a **demo-safe, regression-safe, CI-enforced, portfolio-grade AI-assisted clinical operations product**.

The project now includes:
- a stable dashboard and review workflow
- backend/frontend automated test coverage
- deterministic seeded demo data
- Playwright E2E automation for the main demo path
- screenshot generation for documentation/portfolio use
- CI quality gates for frontend, backend, and E2E
- an interpretable reasoning panel in the trace viewer
- persisted reviewer-note audit visibility for decided runs

All key local validation paths are currently green.

---

## Technical Stack

### Frontend
- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query
- Recharts (lazy-loaded)
- Vitest + React Testing Library
- Playwright

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite for local/demo
- Postgres compatibility via Alembic
- Pytest

---

## Completed Phases

### Phase 12 — Dashboard MVP Shell
- Established dashboard shell and core layout.

### Phase 13 — Review Actions + Donut Chart
- Implemented approve/reject review actions.
- Added interactive routing distribution donut chart.

### Phase 14 — Editable Approval Flow
- Preserved raw model output vs edited JSON.
- Refactored chart architecture.
- Cleaned up review-id lookup using custom hooks.

### Phase 15 — Backend Contract Alignment
- Added `pending_review_id` to run detail response.
- Implemented real bucketed time-series endpoint:
  - `GET /api/dashboard/stats/timeseries?bucket=day`
- Enabled real trend chart using shared routing-series config.

### Phase 16 — Testing, QA, Operator-Proofing
- Added backend coverage for:
  - 409 conflict checks
  - malformed JSON handling
  - timeseries continuity
- Installed frontend test stack:
  - Vitest
  - RTL
  - jsdom
- Added 25 frontend tests.
- Added widget-level error boundaries.
- Added dev-only debug overlay.
- Lazy-loaded Recharts and reduced dashboard first-load JS from ~238 kB to ~130 kB.

### Phase 17 — Deployment Readiness & Demo Packaging
- Made SQLite the local/demo default.
- Enabled startup table creation for SQLite.
- Preserved Alembic for Postgres workflows.
- Added CORS middleware with `CORS_ORIGINS`.
- Added deterministic `seed_demo.py` with 19 runs covering:
  - normal paths
  - review paths
  - edited approval path
  - reject path
- Reworked docs:
  - `README.md`
  - `docs/DEPLOYMENT.md`
  - `docs/DEMO_RUNBOOK.md`
  - `docs/ENGINEERING_DECISIONS.md`

### Phase 18 — E2E Demo Automation & Screenshot Pipeline
**Status: complete and validated**

Implemented:
- Playwright E2E infrastructure using system Chrome:
  - `channel: "chrome"`
  - chosen because bundled Playwright browser download was geo-blocked locally
- `webServer` launches:
  - isolated self-seeding backend using `caretrace_e2e.db`
  - production frontend build for accurate screenshots
- API-for-setup, UI-for-flow strategy
- Deterministic browser tests for:
  - happy path edit + approve
  - reject flow
  - already-decided run with no actions
- Screenshot capture pipeline writing to:
  - `docs/screenshots/`

Validation:
- `npm run test:e2e` → **3 passed**
- `npm run e2e:screens` → **4 screenshots generated**

Key engineering note:
- Tests assert the **durable post-decision state**
  instead of transient success UI, because the run-detail refetch unmounts the review panel after decision.

### Phase 19 — CI Quality Gate & Demo Artifact Automation
**Status: complete**

- Single GitHub Actions workflow (`.github/workflows/ci.yml`) on push / PR / manual dispatch, with cancel-in-progress concurrency.
- Jobs:
  - **frontend** — `npm run ci:frontend` (typecheck + unit + production build).
  - **backend** — `uv sync --extra dev` + `uv run pytest`.
  - **e2e** — gated behind frontend + backend; installs the real Chrome channel; runs `npm run ci:e2e`; uploads the Playwright HTML report always and traces on failure.
  - **screenshots** — `main` / dispatch only; uploads `docs/screenshots/*.png`.

### Phase 20 — Trace Explanation & Clinical Reasoning Panel
**Status: complete and validated**

- Added a deterministic `reasoning_summary` (new `Run` column + Alembic `0003`) built by a shared `build_reasoning_summary()` used by both the live pipeline and the demo seed — the model never narrates itself.
- Exposed `reasoning_summary` + `reviewer_notes` on the run-detail read model.
- New **Reasoning explanation** panel in the trace viewer: color-coded confidence meter, clinical policy violations, a step-by-step decision path, and a read-only reviewer-notes audit trail on decided runs.
- Reused existing data (`Run.confidence`, `ValidationLog`/issues, `ReviewItem.reviewer_notes`) rather than adding parallel columns.

Validation: 86 backend + 25 frontend tests green; E2E (3) incl. reviewer-note round-trip; 4 screenshots regenerated.

### Phase 21 — AI Reviewer Assistant
**Status: complete and validated**

An advisory "AI reviewer assistant" in the trace viewer that gives the operator a deterministic second read of the extracted output.

- **Backend**
  - `app/services/assistant.py` — `AssistantService.analyze_review()` (async seam ready for a real LLM) over a pure, deterministic `analyze_edit()`:
    - **content risks** — high-alert free-text keywords, missing medication doses, and out-of-range vitals;
    - **diff risks** — dose changes and removed medications between the original extraction and the edit;
    - **synthetic confidence** derived from edit magnitude + flagged-risk count.
  - Vital thresholds are held **in lockstep with `app/services/validation.py`** so the assistant never contradicts the routing engine.
  - `POST /api/runs/{run_id}/analyze` (`app/schemas/assistant.py`) — 404 for unknown run, 422 for a non-object `edited_output`. Advisory only: it never mutates the run.
- **Frontend**
  - `components/reviewer/ai-assistant-panel.tsx` — "Get AI analysis" button, loading skeleton, **Stable** vs **Risk alert** (amber) states, assistant confidence, and the suggestion; mounted below the reasoning panel. **Hidden once a run is decided** (reviewed/rejected).
  - Shared types (`AssistantAnalysis` / `AssistantAnalyzeRequest`), `lib/api/assistant.ts`, and `lib/hooks/use-assistant.ts` (read-only mutation, no cache invalidation).
- **Human-in-the-loop:** the assistant is strictly advisory — it never approves, rejects, or persists anything.

Validation: **98 backend** + **30 frontend** tests green; `tsc` clean; production build clean (no new deps); E2E happy path now runs the assistant and asserts a surfaced risk. 

### Phase 22 — Observability & Production Telemetry
**Status: complete and validated**

A thin, local-first observability layer — no external vendors, collectors, Docker, or metrics stack.

- **Backend**
  - `app/core/logging.py` — stdlib-only JSON log formatter + a request-scoped `request_id` `contextvar`, so every log emitted during a request is auto-tagged. `configure_logging()` (idempotent) + `log_event()` helper.
  - `app/core/middleware.py` — `RequestContextMiddleware` (**pure ASGI**, deliberately not `BaseHTTPMiddleware` — the latter added ~2–3s latency to sync endpoints under real uvicorn): generates or preserves `X-Request-ID`, times each request, echoes the id on the response, and emits one structured `http_request` event (method/path/status/`duration_ms`). CORS `expose_headers` lets the browser read the id.
  - `app/core/telemetry.py` — explicit domain helpers (no framework) for the critical flows: run-detail fetch, review approve/reject/conflict/not-found, assistant request/success/failure (`outcome` = `stable`/`risk_alert`), dashboard stats/timeseries, seed completion. **Safe metadata only** — never raw clinical text.
  - Instrumented `runs.py`, `reviews.py`, `dashboard.py`, `seed_demo.py`; wired logging + middleware into `main.py`.
- **Frontend**
  - `lib/telemetry.ts` — in-memory, capped, subscribable telemetry store (+ `startSpan`), console-mirrored in dev only. No external SDK.
  - `lib/api/client.ts` — records an `api_request` event per call with latency and the `X-Request-ID` read back from the response.
  - Telemetry on the assistant + review mutations and on the error boundary (`widget_error`).
  - `components/dev/observability-panel.tsx` — dev-only (opt-in in prod via `NEXT_PUBLIC_OBSERVABILITY=1`) panel showing recent request ids, API latencies, last assistant result, and the event stream; mounted in the dashboard layout.
- **Privacy:** logs and telemetry carry ids/statuses/counts only — enforced at the helper boundary.

Validation: **107 backend** + **41 frontend** tests green; `tsc` clean; `ci:frontend` (typecheck + unit + build) clean, no new deps; E2E suite still green (the panel is dev-only, so production E2E is unaffected). No DB migration/reseed required.