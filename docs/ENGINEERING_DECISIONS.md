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

**Decision.** 86 backend tests (schema/clinical validation, retry, confidence, routing, persistence, endpoints, and Phase-16 edge cases) and 25 frontend tests (Vitest + React Testing Library) covering review-action validation, chart state machines, KPI cache-invalidation-after-mutation, and the error boundary.

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
