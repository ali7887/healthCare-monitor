# CareTrace (healthCare-monitor) - Project Status & Context Sync

## Technical Stack
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS, Shadcn UI, Recharts (lazy-loaded), React Query.
- Backend: FastAPI, SQLAlchemy, SQLite/Postgres (portable persistence), Pydantic, Pytest.

## Completed Phases Summary
- Phase 12: Dashboard MVP Shell & core layout.
- Phase 13: Operational Review Actions (Approve/Reject API integration) & Interactive Recharts Donut Chart.
- Phase 14: Editable Approval Flow (preserving raw model output vs edited JSON), Chart architecture refactor, and review-id lookup cleanup via custom hooks.
- Phase 15: Backend Contract Alignment. Added `pending_review_id` to RunDetailResponse (batch-loaded via selectinload to avoid N+1). Implemented real bucketed time-series endpoint `GET /api/dashboard/stats/timeseries?bucket=day`. Enabled real `TrendAreaChart` using shared `ROUTING_SERIES` config.
- Phase 16: Testing, QA & Operator-Proofing. Added 10 backend tests (409 conflict checks, malformed JSON, timeseries continuity). Installed Vitest/RTL/jsdom, added 25 frontend tests. Added widget-level Error Boundaries, dev-mode Debug Overlay, and lazy-loaded Recharts (reducing dashboard First Load JS from 238kB to 130kB).
- Phase 17: Deployment Readiness & Demo Packaging. Made SQLite the local/demo default (zero-infra; tables auto-create on startup for SQLite, Alembic for Postgres). Added CORS middleware (CORS_ORIGINS). Added `app/seed_demo.py` — deterministic demo dataset (19 runs) spanning every routing path incl. an edited approval. Rewrote README, refined docs/DEPLOYMENT.md, added docs/DEMO_RUNBOOK.md + docs/ENGINEERING_DECISIONS.md, softened a few demo-facing error strings, and added a backend .gitignore.

- Phase 18: E2E & Screenshots (VALIDATED). Playwright with system Chrome
  (`channel: "chrome"`; the Playwright browser CDN is geo-blocked on the dev
  machine). `webServer` launches an isolated, self-seeding backend
  (`caretrace_e2e.db`) + a production frontend build; tests use API-for-setup,
  UI-for-flow. 3 E2E tests pass (edit+approve happy path, reject, already-decided
  run shows no actions) and 4 screenshots generate to `docs/screenshots/`. Key
  fix: assert the durable post-decision state (run refetches → review panel
  unmounts), not the transient success banner.
- Phase 19: CI Quality Gate. Single GitHub Actions workflow
  (`.github/workflows/ci.yml`): frontend (`ci:frontend` = typecheck+unit+build),
  backend (`uv run pytest`), and E2E (`ci:e2e`, gated behind the fast jobs) are
  blocking; a screenshots job (main/manual) uploads PNGs as an artifact. CI runs
  the same local commands; installs real Chrome via
  `npx playwright install --with-deps chrome`. Playwright report + failure traces
  uploaded as artifacts.

## Current Verification Status
- Backend: `uv run pytest` -> 86 passed.
- Frontend: `npm run ci:frontend` -> typecheck clean, 25 unit tests pass, build clean (dashboard First Load JS 130 kB).
- E2E: `npm run test:e2e` -> 3 passed; `npm run e2e:screens` -> 4 screenshots written to docs/screenshots/.
- CI: `.github/workflows/ci.yml` validated (YAML parses; 4 jobs; e2e gated on frontend+backend; screenshots on main/dispatch).
- Demo: `uv run python -m app.seed_demo` -> 19 runs (isolated E2E DB is separate: caretrace_e2e.db).
