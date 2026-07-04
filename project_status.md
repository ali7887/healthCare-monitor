Project Status Report & Phase 15 Blueprint

Project: CareTrace (healthCare-monitor)
Date: July 3, 2026
Project Lead: Ali (Fullstack AI Engineer & UI/UX Designer)
System Architecture: Next.js (Frontend MVP) | FastAPI & Pydantic (Backend RAG Engine) | PostgreSQL & Drizzle (Data Access)
Theme: Clinical Calm (Teal/Slate UI)
1. Executive Summary

CareTrace (healthCare-monitor) is a high-reliability clinical evaluation dashboard designed to monitor, audit, and validate Retrieval-Augmented Generation (RAG) pipelines in healthcare environments. The project emphasizes operational visibility, data density, and rigorous human-in-the-loop validation, with a presentation quality suitable for German fintech/healthtech and automotive SEO/AI recruitment teams.

As of Phase 14, the frontend has progressed from a static prototype into an interactive, fully type-safe dashboard with editable human-review states, an isolated mock-data adapter layer prepared for backend integration, and a decoupled component structure for charts and system statistics. The codebase is now structurally ready for backend contract alignment and live data integration.
2. Completed Phases & Historical Log
Phase 12: Next.js Dashboard MVP

Status: Completed

    App Shell Integration: Implemented branding sidebar, sticky top navigation bar, and responsive mobile drawers.

    KPI Metrics Strip: Designed and coded cards for active runs, pass/fail review rates, and latency.

    Three-Column Trace Viewer: Built metadata display, interactive transcript explorer, and decision panel.

    Runs Data Table: Built structured, filterable, and paginated data tables with type-safe routing.

    Security Patches: Upgraded Next.js to version 15.5.20 to address critical CVE vulnerabilities.

Phase 13: Operational Actions & Visualization

Status: Completed

    Review Mutation Integration: Developed React Query mutations connecting the UI directly to POST /api/reviews/{id}/action.

    Cache Invalidation: Configured automated invalidation for ["dashboard"], ["runs"], and ["reviews"] upon action success.

    Interactive Routing Donut Chart: Replaced static CSS bars with a dynamic, theme-consistent Recharts donut visualization featuring custom tooltips and a total count center.

Phase 14: Review Workflow Hardening & Observability Readiness

Status: Completed

    Editable Approval Flow:

        Integrated an "Edit output before approving" toggle showing a monospace JSON editor.

        Implemented client-side JSON schema validation, safely parsing inputs without relying on the any type.

        Explicitly decoupled original outputs from edited payloads, displaying an "edited" state badge.

        Ensured per-action loading states, disabled buttons, and accessibility structures (aria-live="polite", role="alert").

    Contract-Gap Containment:

        Created use-pending-review-id.ts to isolate the temporary backend contract gap.

        The hook leverages cached queries to map run_id to its corresponding review_id without introducing duplicate network requests.

    Observability-Ready Chart Architecture:

        Split chart components into ChartCard (state machine handling loading, empty, and error states), DonutChart, and ChartLegend.

        Added ThroughputTrendChart with an honest empty-state UI to prevent fabricating fake data before backend APIs are ready.

    Compilation & Verification:

        npx tsc --noEmit completed without errors.

        npm run build executed successfully, producing 7 generated routes including dynamic page paths.

        Bundle size verified at approximately 225 kB first-load JS due to Recharts integration.

3. Current Architectural State (Frontend)

caretrace/frontend/src/
├── components/
│   ├── charts/
│   │   ├── chart-card.tsx            # Presentational wrapper with state machine
│   │   ├── donut-chart.tsx           # Pure Recharts donut wrapper
│   │   ├── chart-legend.tsx          # Numerical color-coded legend
│   │   └── throughput-trend.tsx      # Honest empty-state placeholder for time-series
│   ├── dashboard/
│   │   └── routing-distribution.tsx  # Layout container mapping dashboard stats to charts
│   ├── runs/
│   │   ├── review-actions.tsx        # Human-in-the-loop form, JSON editor, actions
│   │   └── run-detail.tsx            # Container rendering trace viewer & review rail
│   └── ui/
│       ├── button.tsx                # Modified to support destructive variations
│       └── textarea.tsx              # Base form control for notes/JSON payloads
├── lib/
│   ├── api/
│   │   ├── client.ts                 # Shared HTTP Client with typed error parsing
│   │   ├── reviews.ts                # Fetching and mutation API definitions
│   │   └── types.ts                  # Domain models (ReviewStatus, ReviewAction, etc.)
│   └── hooks/
│       ├── use-reviews.ts            # Fetches global review list
│       ├── use-run-action.ts         # Mutation hook for POST /api/reviews/{id}/action
│       └── use-pending-review-id.ts   # Temporary lookup adapter for run-to-review translation

4. Definition of Done for the Entire Project

To consider CareTrace fully finalized and ready for job-application showcases, portfolio reviews, and code walkthroughs, it must satisfy the following:

    No Frontend Workarounds: All query hooks match backend models directly without UI-side lookup scanning.

    True Observability: The dashboard must display real, historical time-series graphs powered by the server.

    Full Integration Polish: The local dev setup (npm run dev + FastAPI port 8000) allows real-time execution, editing, and approval with instant DB commits.

    Test Suite Coverage: Critical user flows such as JSON parsing, review submission, and API error states are covered by component or integration tests.

    Deployment & Showcase Artifacts: Code is deployed, environment parameters are cleanly separated, and a professional repository architecture README with data-flow diagrams is finalized.

5. Roadmap to Completion: Final Phases

                     ┌───────────────────────────────────────┐
                     │ Phase 15: Backend Contract Alignment  │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ Phase 16: Test Coverage & Hardening   │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ Phase 17: Production & Portfolio Close│
                     └───────────────────────────────────────┘

Phase 15: Backend Contract Alignment & Live API Integration

Target: Refactor backend schemas and integrate live endpoints to delete workarounds.

    Backend Refactoring (FastAPI):

        Add optional/nullable pending_review_id field to the database models and the frontend-facing RunDetailResponse schema.

        Implement a time-series stats API endpoint: GET /api/dashboard/stats/timeseries?bucket=day returning real chronological aggregations of RAG runs.

    Frontend Refactoring:

        Delete use-pending-review-id.ts entirely.

        Refactor review-actions.tsx to read the review ID directly from the run payload.

        Replace the placeholder in ThroughputTrendChart with a fully active Recharts line chart parsing real time-series payloads.

    Payload Verification:

        Ensure edited_output parameters correctly update run records on the backend.

Phase 16: Test Coverage & Robustness Hardening

Target: Establish confidence in interactive UI behaviors and state transitions.

    Unit & Integration Testing:

        Write Vitest/React Testing Library tests for review-actions.tsx verifying:

            JSON validation error handling, including malformed JSON parsing alerts.

            Button disabled states while mutation is pending.

            Output modifications display the "edited" badge indicator.

    Edge-Case Validation:

        Test behavior during connection dropouts, high-latency states, and unauthorized response errors (401/403).

Phase 17: Production Deployment, Documentation & Portfolio Packaging

Target: Make the codebase ready for immediate reviewer consumption.

    Infrastructure: Configure unified deployments with Docker Compose or Vercel + Fly.io/Render templates.

    Security Check: Eliminate leftover debug values, check CORS configs, and ensure production build bundles are fully optimized.

    Documentation: Author a comprehensive technical README containing:

        Architecture overview and data cycle graph.

        Quick-start guide for both Docker and local dev.

        Clear explanations of design choices, including why a decoupled chart architecture was used and how custom type safety supports clinical evaluations.

6. Current Status Assessment

CareTrace is now in a strong pre-integration state.
What is solid

    The frontend is modular, typed, and interaction-ready.

    Human review flows are robust and accessible.

    Charting is compartmentalized to support real metrics ingestion.

    The codebase compiles cleanly and builds successfully.

    Temporary gaps are isolated rather than spread through the app.

What remains

    The frontend still depends on a stopgap review ID mapping hook.

    The throughput trend visualization is not yet backed by real server time-series data.

    Backend response contracts need alignment with the frontend’s active review workflow.

    Test coverage and deployment packaging are not yet at showcase standards.

Practical implication

Phase 15 is the critical bridge between a polished frontend prototype and a truly integrated product demo. Completing it removes the last major architectural workaround and unlocks the remaining validation and production steps.
7. Phase 15 Blueprint
7.1 Objective

Phase 15 will align the backend and frontend contracts so that CareTrace uses live API data end-to-end without temporary translation layers.
7.2 Success Criteria

Phase 15 is complete when all of the following are true:

    RunDetailResponse includes pending_review_id as a nullable field.

    The frontend no longer uses use-pending-review-id.ts.

    review-actions.tsx reads review identity directly from the run payload.

    GET /api/dashboard/stats/timeseries?bucket=day returns real grouped historical metrics.

    ThroughputTrendChart renders a real line chart from server data.

    Backend edited_output persistence is verified.

    TypeScript compilation remains clean.

    Backend tests continue to pass.

8. Phase 15 Implementation Plan
Step 1: Backend Schema Alignment

Update the FastAPI and Pydantic models so that run detail responses include:

    pending_review_id: UUID | null

This field should be:

    Optional for backward compatibility.

    Reflected consistently across the DB model, API response schema, and any serializer logic.

    Safe for consumers that may receive older records with no pending review.

Step 2: Add Time-Series Stats Endpoint

Implement:

    GET /api/dashboard/stats/timeseries?bucket=day

The endpoint should return:

    Chronological run buckets.

    Aggregated counts for:

        auto_saved

        human_review

        rejected

The returned payload should be stable, predictable, and directly consumable by the frontend chart layer.
Step 3: Remove Frontend Lookup Workaround

Delete:

    use-pending-review-id.ts

Then refactor:

    review-actions.tsx

The component should consume pending_review_id directly from the run detail payload and no longer scan cached data to reconstruct the review ID.
Step 4: Activate Throughput Trend Visualization

Replace the empty-state fallback in:

    ThroughputTrendChart

with:

    A live Recharts line chart based on the new time-series API payload.

The chart should:

    Respect the existing clinical calm visual language.

    Handle loading, empty, and error states honestly.

    Maintain the same design system consistency as the other chart components.

Step 5: Verify Edited Output Persistence

Ensure submitted edited_output content:

    Reaches the backend unchanged.

    Is associated with the correct review/run record.

    Persists through the database update path.

    Produces the expected review state transitions.

9. Risks and Mitigations
Risk: Contract mismatch between frontend and backend

Mitigation: Introduce the nullable field in a backward-compatible way and update response schemas before removing the frontend workaround.
Risk: Time-series endpoint returns sparse or inconsistent buckets

Mitigation: Define explicit bucket semantics and test date grouping logic against representative run histories.
Risk: Chart rendering complexity increases bundle cost

Mitigation: Keep the chart architecture modular and reuse the existing wrapper/state-machine structure to avoid duplication.
Risk: Edited output submission could drift from the original review identity

Mitigation: Use direct pending_review_id propagation from the run detail payload and verify through integration checks.
10. Tomorrow’s Operational Starting Point

When starting work tomorrow, use the following prompt to initialize implementation of Phase 15:

    You are working on the caretrace/healthCare-monitor project.
    Phase 14 is fully complete and verified.
    Your objective is to implement Phase 15: Backend Contract Alignment & Live API Integration.

    Tasks to accomplish:

        Review/Update the Backend (FastAPI):

            Modify the RAG Run detail response schema (RunDetailResponse) to include a nullable/optional pending_review_id: UUID | null property.

            Implement GET /api/dashboard/stats/timeseries?bucket=day to group runs by day, returning historical counts (auto_saved, human_review, rejected).

            Ensure database queries for the time-series stats map correctly to the engine.

        Refactor Frontend Data Access:

            Deprecate use-pending-review-id.ts completely.

            Refactor review-actions.tsx to consume pending_review_id directly from the active run detail response.

            In ThroughputTrendChart, replace the empty-state fallback UI with a real Recharts line chart component displaying the actual response arrays from the new time-series endpoint.

        Verification:

            Ensure clean compilation with npx tsc --noEmit and build passing in caretrace/frontend.

            Confirm backend FastAPI test suite still executes cleanly.

11. Final Note

CareTrace is now past the prototype stage and has entered the final integration phase. Phase 15 is the decisive step that will remove the last architecture gap, connect the product to true historical backend data, and prepare the foundation for test coverage and production packaging.

Once Phase 15 is complete, the project will be ready for the final hardening and portfolio-close stages.

---

### Phase 15 — Contract Alignment, Time-Series Metrics, Integration Cleanup

Status: Complete and verified (both Phase-14 recommendations delivered)

Backend:
- RunDetailResponse now includes pending_review_id (nullable), populated from the
  run's pending ReviewItem via persistence.pending_review_id(). get_run and
  get_runs both selectinload review_items (batched, no N+1).
- New GET /api/dashboard/stats/timeseries?bucket=day&days=N —
  persistence.get_dashboard_timeseries buckets runs by day x routing decision and
  fills empty days with zeros (computed in Python for SQLite/Postgres portability;
  real counts, no synthesized values). Typed DashboardTimeseriesResponse.
- Tests: +4 (test_phase15_endpoints) -> full suite 76 passing.

Frontend:
- Removed the /reviews-by-run_id workaround: deleted usePendingReviewId,
  useReviews, and getReviews; ReviewActions reads run.pending_review_id directly.
  Approve/reject query invalidation unchanged.
- Real trend chart: useDashboardTimeseries + a stacked-area TrendAreaChart drive
  ThroughputTrendChart (replacing the placeholder), reusing the Phase-14 ChartCard
  states + ChartLegend. A shared ROUTING_SERIES config (label/color) is the single
  source of truth for both the donut and the trend (no duplicated status mapping).

Verification:
- backend: uv run pytest -> 76 passed
- frontend: npx tsc --noEmit clean; npm run build -> 7 routes, types valid.

## Phase 16 — Testing, Reliability, QA & Operator-Proofing (complete)

Backend:
- Terminal review decisions are now immutable: apply_review_action raises
  ReviewConflictError on a non-pending review; the /reviews/{id}/action route maps
  it to 409 (distinct from 404 for an absent review). Guards against re-approving/
  re-rejecting an already-decided run.
- Tests: +10 (test_phase16_review_edges) — 409 on re-decision, malformed
  edited_output -> 422 (wrong type / non-object / unknown field / bad action),
  timeseries gap-fill continuity + empty-db zeros, and a donut/trend routing-group
  alignment regression (stats totals == summed timeseries per decision).
- Full backend suite: 86 passing.

Frontend (new test infrastructure — dev-only deps):
- Added Vitest + React Testing Library + jsdom; `npm run test` / `test:watch`.
  vitest.config.ts (jsdom, @ alias), src/test/setup.ts (jest-dom + matchMedia/
  ResizeObserver stubs), src/test/utils.tsx (renderWithClient + test QueryClient).
- 25 tests / 7 files: ReviewActions (JSON validation, error/success, disabled-
  while-pending, edited-approve payload), ChartCard state machine, DonutChart +
  TrendAreaChart (Recharts ResponsiveContainer mocked to a fixed size), KpiStrip
  render + cache-invalidation-after-mutation, KpiStrip error/loading, ErrorBoundary.

Operator-correctness & reliability:
- ErrorBoundary (plain React class, no new libs): dashboard widgets wrapped
  individually so one failure never blanks the page; role=alert fallback with a
  reset ("Try again") and dev-only error detail.
- React Query already tuned for reliability (staleTime 30s, retry 1,
  refetchOnWindowFocus off) — left as-is.

Observability & performance:
- Dev-only DebugPanel + DashboardDebug: pins the raw timeseries payload, the
  ROUTING_SERIES mapping, and query statuses in-app; tree-shaken out of production.
- Recharts dynamic-imported (next/dynamic, ssr:false) in both chart wrappers ->
  dashboard First Load JS 238 kB -> 130 kB (Recharts moved to a lazy chunk).

Verification:
- backend: uv run pytest -> 86 passed
- frontend: npm run test -> 25 passed; npx tsc --noEmit clean; npm run build ->
  7 routes, no warnings, dashboard First Load JS 130 kB.
- See docs/QA_CHECKLIST.md for the review-workflow QA readiness checklist.