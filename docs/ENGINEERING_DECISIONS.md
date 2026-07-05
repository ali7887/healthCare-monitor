# Engineering Decisions

A concise record of the non-obvious choices in healthCare-monitor and *why* they were made. Written for a reviewer or interviewer who wants to understand the reasoning, not just the result. Each entry states the decision, the alternative it beat, and the tradeoff.

---

## 1. Confidence is derived locally, never asked of the model

**Decision.** The pipeline computes confidence from concrete validation outcomes: `base 1.0 − capped penalties` (failure, retry, severity, type), clamped to `[0,1]`. The full breakdown is persisted with each run.

**Why.** A model's self-reported confidence is unreliable and unfalsifiable — it can be wrong *and* certain. Deriving the score from deterministic checks makes it **explainable and reproducible**: the same output always yields the same score, and a reviewer can see exactly which penalty moved it. This is the core "deterministic validation over model self-trust" principle.

**Tradeoff.** The scoring formula is a heuristic that must be tuned and justified, rather than "free" from the model. That's the point — it lives in versioned code with tests.

## 2. Routing is grouped by routing *decision*, and the whole dashboard uses one series config

**Decision.** Runs are grouped by `routing_decision` (`auto_save` / `human_review` / `reject`) for both the distribution donut (`/dashboard/stats`) and the throughput trend (`/dashboard/stats/timeseries`). A single frontend `ROUTING_SERIES` config owns the label + color + key mapping for both.

**Why.** Routing decision is the operationally meaningful axis — it answers "what did the system *do* with this output?" Grouping by raw `status` instead would split resolved reviews (`reviewed`) away from the human-review bucket and blur the operational picture. Using one config for both charts means they physically cannot use different colors or groupings; a regression test asserts that per-decision totals from `/stats` equal the summed timeseries counts, so the two surfaces can never silently drift.

**Tradeoff.** A `reviewed` run still counts under `human_review` in the donut (that's where it was routed). This is intentional and honest, but it means the donut reflects *routing*, not *current status* — documented so it isn't mistaken for a status breakdown.

## 3. `pending_review_id` was added to the run-detail contract

**Decision.** `RunDetailResponse` carries `pending_review_id: UUID | None`, populated server-side and batch-loaded via `selectinload(Run.review_items)`.

**Why.** The review UI needs the review item's id to submit a decision. Earlier phases resolved it on the frontend with a workaround (a second lookup mapping `run_id → review_id`). That put backend knowledge in the client and risked extra requests. Moving it into the contract makes the run detail **self-sufficient**: the review panel reads one field, with no follow-up query. `selectinload` keeps it a single batched query — no N+1.

**Tradeoff.** A slightly wider read model. Worth it: the client is simpler, and there is one obvious source of truth for "which review does this run belong to."

## 4. Editable approval preserves the original model output

**Decision.** When a reviewer edits before approving, the correction is stored as `ReviewItem.edited_output` and copied to `Run.final_output`. The original `Run.parsed_output` and `Run.raw_model_response` are **never overwritten**.

**Why.** Auditability. In a clinical documentation context you must always be able to answer "what did the model produce, and what did the human accept instead?" Overwriting the original would destroy that comparison. Keeping raw / parsed / final as distinct fields makes the human's intervention a visible, reviewable event rather than a silent mutation.

**Tradeoff.** Three representations of "the output" to reason about. The naming (`raw_model_response` → `parsed_output` → `final_output`) is chosen to make the progression obvious.

## 5. Terminal review decisions are immutable (409 conflict guard)

**Decision.** `apply_review_action` raises `ReviewConflictError` if the target review is not `pending`; the route maps it to **HTTP 409** — distinct from **404** for a review that doesn't exist.

**Why.** A recorded human decision is a fact, not a mutable field. Without the guard, re-approving or re-rejecting an already-decided run would silently transition state again (or flip approved↔rejected). The 409 makes the invariant explicit and gives the client a precise, actionable error. Keeping 404 separate preserves the distinction between "gone" and "already decided."

**Tradeoff.** The service layer needs a typed exception the API translates, rather than returning a bare `None`. That small amount of structure is what makes the two failure modes distinguishable.

## 6. SQLite by default, Postgres-ready — with dialect-portable models

**Decision.** The default `DATABASE_URL` is a local SQLite file. Models avoid dialect-specific features: enums are `VARCHAR + CHECK` (`native_enum=False`), ids/JSON use generic `Uuid`/`JSON` types, and timestamps use Python-side defaults. SQLite tables auto-create on startup; Postgres uses Alembic.

**Why.** Reproducibility and demo ergonomics. A reviewer can clone, seed, and run the whole system with **no external infrastructure and no API key**. Because the models are portable, the *same* code runs on Postgres for a production-like setup — the tests already exercise the models on SQLite, which is the same DDL the app uses.

**Tradeoff.** SQLite isn't a production database (concurrency, types). That's fine: it's the demo default, and the portability work means switching to Postgres is a one-line env change plus a migration.

## 7. Pure compute core, persistence at the edge

**Decision.** The pipeline, validation, confidence, and routing services are pure functions with no ORM imports. Persistence (`persist_run`, `apply_review_action`) happens only at the API boundary and commits within a single transaction per run.

**Why.** It keeps the reliability logic trivially unit-testable (no database fixture needed to test a routing threshold) and avoids the models→db bootstrap import cycle. The service-layer `RoutingDecision` is bridged to the persisted enum *by value*, so the compute layer never imports the ORM.

**Tradeoff.** A small amount of mapping code at the boundary (service enums ↔ persisted enums). In exchange, the core stays framework-agnostic.

## 8. Testing: pytest + Vitest/RTL, covering behavior and contracts

**Decision.** 117 backend tests (schema/clinical validation, retry, confidence, routing, persistence, endpoints, the AI-assistant heuristics, observability, health/readiness + deployment config, and edge cases) and 41 frontend tests (Vitest + React Testing Library) covering review-action validation, chart state machines, KPI cache-invalidation-after-mutation, the error boundary, the AI-assistant panel, and the telemetry/observability layer.

**Why.** The highest-value guarantees are behavioral: does an invalid edit get blocked, does the dashboard update after a decision, do the donut and trend agree. Charts are tested with `ResponsiveContainer` mocked to a fixed size so they render deterministically under jsdom. The one intentional-rejection test drives its error path through a stubbed hook rather than a rejected query, to avoid the runner's unhandled-rejection race.

**Tradeoff.** Chart tests assert structure/behavior, not pixels — visual regressions still need a human/visual pass (noted in the QA checklist).

## 9. React Query for server state; invalidate on mutation

**Decision.** All reads go through TanStack Query with `staleTime` 30s, `retry` 1, and `refetchOnWindowFocus` off. A review action invalidates `["dashboard"]`, `["runs"]`, and `["reviews"]` on success.

**Why.** Server state is cached and consistent without hand-rolled fetching, and reliable without being spammy (one retry, no focus-thrash). Invalidation-on-mutation means one decision refreshes the KPI strip, charts, runs list, and queue together, so the UI is never stale after an action — proven by a cache-invalidation test.

**Tradeoff.** A cache to reason about. The keys are namespaced (`["dashboard", ...]`) so a single invalidate call fans out correctly.

## 10. Recharts is dynamically imported

**Decision.** The donut and trend chart components are loaded via `next/dynamic` (`ssr: false`) with a skeleton fallback.

**Why.** Recharts is the heaviest client dependency and is only needed on the dashboard. Lazy-loading it cut the dashboard's First Load JS from **~238 kB to ~130 kB** without changing behavior — the chart container's existing loading state covers the brief chunk fetch.

**Tradeoff.** A momentary skeleton on first dashboard paint. Acceptable, and it reuses the loading state the chart card already had.

## 11. Observability is thin, local-first, and privacy-safe

**Decision.** Observability is a deliberately small, dependency-free layer rather than an external stack. Backend: a JSON log formatter over stdlib `logging` (`app/core/logging.py`), an `X-Request-ID` correlation + timing middleware (`app/core/middleware.py`), and explicit domain telemetry helpers for the critical flows (`app/core/telemetry.py`). Frontend: an in-memory telemetry store (`lib/telemetry.ts`), correlation-id capture in the fetch client, and a dev-only observability panel. No OpenTelemetry collector, Prometheus/Grafana, Docker, or SaaS vendor.

**Why.** The value we wanted was **diagnosability and correlation** — being able to take a latency or failure seen in the UI and find the exact backend log that produced it — not a metrics platform. A correlation id that is generated-or-preserved per request, echoed on the response (`expose_headers`), bound to a `contextvar` so every downstream log carries it automatically, and read back by the frontend delivers that end-to-end trace with essentially zero infrastructure. Structured JSON logs keep the output grep-able and machine-readable without a shipper. Keeping it thin also keeps local startup a single command and CI deterministic.

**Pure ASGI middleware, not `BaseHTTPMiddleware`.** The correlation/timing middleware is implemented as a bare ASGI class (`__call__(scope, receive, send)`), not Starlette's `BaseHTTPMiddleware`. During Phase 22 the `BaseHTTPMiddleware` version passed all unit tests (via `TestClient`) but added **~2–3s of latency to synchronous (`def`) endpoints under real uvicorn** — enough to time out the Playwright review-flow E2E — because `BaseHTTPMiddleware` runs the downstream app in a separate anyio task and pumps the response through a memory stream, which contends with the threadpool that serves sync endpoints. The pure-ASGI wrapper removed the regression (review action back to ~0.4s) and keeps the `contextvar` in the same task as the endpoint. Lesson: middleware performance must be checked against a real server, not just `TestClient`.

**Privacy.** Telemetry and logs carry **safe metadata only** — ids, statuses, counts, outcome categories (`stable` / `risk_alert`) — and never raw transcripts, clinical notes, or full payloads. This is a hard rule for a healthcare-adjacent system, enforced at the helper boundary (helpers take scalars, not note objects).

**Tradeoff.** No historical aggregation, dashboards, or alerting — logs are point-in-time and the frontend telemetry buffer is in-memory (capped, session-scoped). Acceptable for an MVP/demo; the helper-function seams are the obvious place to forward to a real backend later without touching call sites. The dev observability panel is hidden in production by default and can be opted in with `NEXT_PUBLIC_OBSERVABILITY=1`.

## 12. Deployment is PaaS-first, config-driven, and keeps SQLite as a valid default

**Decision.** The app deploys as a Next.js app on Vercel pointed at a FastAPI service on Render/Railway — no Docker, no Compose, no Kubernetes, and Postgres is *optional*. A single `Settings` layer (`app/core/config.py`) reads `CARETRACE_ENV` (`dev`/`demo`/`production`), `DATABASE_URL`, `CARETRACE_DEMO_SEED`, `CARETRACE_LOG_LEVEL`, and `CORS_ORIGINS`. `start_production.sh` runs `alembic upgrade head` only on a non-SQLite `DATABASE_URL`, optionally seeds, and launches uvicorn with worker/keep-alive tuning. Two probes back the platform health checks: `GET /health` (liveness + DB round-trip) and `GET /ready` (DB + core schema present), both returning **503** on failure. A `deploy` CI job exists but is **manual only** (`workflow_dispatch`, gated behind the quality gates and repository secrets).

**Why.** The goal was a *credible, reproducible* deployment story for a portfolio MVP, not production infrastructure theater. PaaS + managed Postgres removes the ops surface (no container registry, no cluster) while still being "real" — the same dialect-portable models (decision #6) run on the hosted Postgres. Mode is environment-driven so the identical build runs locally, as a public demo, or in production with only env changes; the request/validation logic never branches on mode. Splitting `/health` (cheap liveness, safe as a container health check that a DB blip shouldn't kill unnecessarily — but still surfaces connectivity) from `/ready` (won't accept traffic until the schema is migrated) matches how orchestrators actually route. Keeping the deploy job manual prevents an accidental push from shipping, and gating it on `frontend`/`backend`/`e2e` means a deploy can only follow green checks.

**Boot-time demo seeding is guarded.** In `demo` mode with `CARETRACE_DEMO_SEED=1`, the app seeds the deterministic dataset on startup *only if the database is empty* — so a fresh demo boots with data, but an existing (or production) database is never reset or duplicated. Off by default, so production is never touched implicitly.

**Frontend env is a template, not a committed `.env.production`.** Next.js inlines every `NEXT_PUBLIC_*` value at build time; a committed `.env.production` would bake a placeholder API URL into the bundle (and into CI's build step). The committed file is therefore `.env.production.example`; real values are set in Vercel's dashboard. `NEXT_PUBLIC_API_BASE_URL` is the existing variable name — kept as-is rather than renamed for the sake of the spec, to preserve naming consistency with the fetch client.

**Tradeoff.** SQLite as a demo default is not a production database (concurrency/types) — accepted, because switching is a one-line `DATABASE_URL` change plus the migration the start script already runs. The `deploy` CI job can't be end-to-end verified without live cloud accounts/secrets, so it's written to fail fast with a clear error when a required secret is missing rather than to silently no-op.
