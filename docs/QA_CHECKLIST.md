# QA Readiness Checklist — Review Workflow

Scope: the human-in-the-loop review path, from a run being routed to review
through a recorded decision, plus the dashboard surfaces that reflect it. Each
item notes how it is guarded (automated test) or how to verify it manually.

Legend: ✅ automated · 👁 manual check.

## 1. Routing into review
- ✅ A run whose routing decision is `human_review` creates exactly one pending
  `ReviewItem` (`test_api::test_process_critical_routes_to_review_then_approve`).
- ✅ `auto_save` and `reject`/`failed` runs create **no** review item
  (`test_api`, `test_phase15`).
- ✅ `RunDetail.pending_review_id` is the pending item's id for a `needs_review`
  run and `null` otherwise (`test_phase15_endpoints`).

## 2. Approve / reject decisions (backend contract)
- ✅ Approve transitions review→`approved`, run→`reviewed`; reject transitions
  review→`rejected`, run→`rejected` (`test_api`).
- ✅ Approving with a valid `edited_output` sets the run's `final_output` to the
  correction (`test_persistence::test_apply_review_action_approve_with_edit`); the
  original `parsed_output`/`raw_model_response` are left untouched in the trace by
  design. 👁 If you add field-level editing later, add an assertion that
  `parsed_output` is unchanged after an edited approval.
- ✅ Acting on an **already-decided** review returns **409 Conflict**, not a
  silent re-apply (`test_phase16_review_edges`).
- ✅ Acting on an **unknown** review id returns **404** (distinct from 409)
  (`test_api`, `test_phase16_review_edges`).
- ✅ Malformed `edited_output` is rejected at the contract boundary with **422**:
  wrong field type, non-object (array), and unknown top-level field; an invalid
  `action` value is also 422 (`test_phase16_review_edges`).

## 3. Approve / reject UI (operator-proofing)
- ✅ No pending review id → a no-op message and **no** action buttons render
  (`review-actions.test`).
- ✅ Invalid JSON in the editor blocks approval, shows a `role="alert"` message,
  and does **not** call the API (`review-actions.test`).
- ✅ Non-object edited payload (array) is rejected client-side before submit
  (`review-actions.test`).
- ✅ A valid edited payload is forwarded as the corrected object; reviewer notes
  are trimmed and sent as `null` when blank (`review-actions.test`).
- ✅ Both buttons are disabled while a decision is in flight; success shows a
  `role="status"` confirmation; API failure shows a `role="alert"` with the
  server detail (`review-actions.test`).
- 👁 Keyboard path: Tab reaches notes → edit toggle → JSON editor → Approve →
  Reject in order; after submit, focus/aria-live announces the outcome. Verify
  with keyboard only (no mouse) and a screen reader on the review panel.

## 4. Dashboard reflects decisions
- ✅ After a decision, `useRunAction` invalidates `["dashboard"]`, `["runs"]`,
  and `["reviews"]`; the KPI strip re-fetches and shows the new counts
  (`kpi-strip.test` cache-invalidation case).
- ✅ Donut (stats) and trend (timeseries) never drift: per-decision totals from
  `/stats` equal the summed per-decision timeseries counts
  (`test_phase16_review_edges`).
- 👁 End-to-end: process a critical transcript → open the run → approve/reject →
  confirm the queue empties and the KPI strip + charts update without a manual
  refresh.

## 5. Loading / error / empty resilience
- ✅ `ChartCard` shows error (with retry) over loading over empty over children,
  in that precedence (`chart-card.test`).
- ✅ `KpiStrip` shows an error surface with a working retry, and skeletons while
  loading (`kpi-strip-states.test`).
- ✅ Charts render deterministically and don't crash on an all-zero / empty
  window (`donut-chart.test`, `trend-area-chart.test`).
- ✅ A render-time exception in one dashboard widget is contained by its
  `ErrorBoundary` (role=alert fallback + reset); the rest of the page survives
  (`error-boundary.test`).
- ✅ Timeseries fills missing days with zeros and stays continuous, including an
  empty database (`test_phase16_review_edges`, `test_phase15_endpoints`).

## 6. Reliability & performance guardrails
- React Query: `staleTime` 30s, `retry` 1, `refetchOnWindowFocus` off — reliable
  without hammering the backend.
- Recharts is lazy-loaded (`next/dynamic`, `ssr:false`); dashboard First Load JS
  is ~130 kB (target 230–260 kB).
- Dev-only `DebugPanel` exposes the raw timeseries payload, routing-series
  mapping, and query statuses; it is tree-shaken out of production builds.

## How to run the gates
```
# backend
cd caretrace/backend && uv run pytest        # 86 passing

# frontend
cd caretrace/frontend
npm run test          # 25 passing (Vitest + RTL)
npx tsc --noEmit      # types clean
npm run build         # no warnings; dashboard First Load JS ~130 kB
```

## Known residual risks
- Timeseries is bucketed in Python (portable, honest counts) and reads two
  columns for the whole window; at large scale move to a SQL `date_trunc` +
  `GROUP BY` with a windowed `WHERE`.
- Chart tests assert structure/behavior with a mocked `ResponsiveContainer`, not
  pixel output — visual regressions still need a manual/visual pass.
- No end-to-end (browser) tests yet; sections 3/4's 👁 items are manual.
