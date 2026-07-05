# CareTrace — Product Overview

**Reliable handling of AI-generated clinical documentation: deterministic
validation, full traceability, and human review.**

CareTrace (project: *healthCare-monitor*) turns unstructured nursing/caregiver
transcripts into structured clinical notes, then treats the model's output as
*untrusted* until it has passed deterministic checks. Every run is scored,
routed, and stored as a complete audit trace. Low-confidence or clinically
inconsistent outputs are **flagged for a human** instead of being silently saved.

> This is a portfolio-grade reliability-engineering MVP built around LLM output —
> **not** a certified medical device. It does not diagnose, prescribe, or
> recommend treatment; it structures documentation and surfaces *potential
> inconsistencies* for human review.

---

## Executive summary

Naive "call the model, store the JSON" pipelines fail exactly where healthcare
can't afford it: malformed output, missing fields, clinically implausible values,
and no way to explain *why* a result was trusted. CareTrace makes an LLM feature
**operationally credible**:

- **Deterministic validation over model self-trust.** The model is never asked
  how confident it is; confidence is *derived locally* from concrete validation
  outcomes and persisted as an auditable breakdown.
- **Traceability by default.** Every run stores its raw response, parsed output,
  validation issues, routing decision, and confidence breakdown.
- **Human-in-the-loop as a first-class path**, including *edited approvals* where
  a reviewer's correction is stored without overwriting the original output.
- **Advisory second read.** A deterministic AI reviewer assistant gives the
  operator a second opinion — strictly advisory, never auto-deciding.
- **Local-first observability.** Request correlation ids, structured JSON logs,
  and safe telemetry tie a UI action to the exact backend log — no external vendor.
- **Tested and hardened:** 117 backend tests + 41 frontend tests, per-widget
  error boundaries, an immutable-decision conflict guard, and health/readiness
  probes for production hosting.

---

## Screenshots

Portfolio captures live in [`screenshots/production/`](screenshots/production/)
(regenerate with `npm run e2e:screens:prod`). The canonical demo captures are in
[`screenshots/`](screenshots/).

| View | Image |
|---|---|
| Dashboard — KPIs, routing donut, throughput trend | `screenshots/production/01-dashboard-overview.png` |
| Run detail — trace + reasoning panel | `screenshots/production/02-run-detail-trace.png` |
| Reasoning panel — confidence + decision path | `screenshots/production/02-run-detail-trace.png` |
| AI reviewer assistant — advisory second read | `screenshots/production/05-assistant-panel.png` |
| Review — edit before approving | `screenshots/production/03-review-edit-state.png` |
| Post-decision — durable reviewed state | `screenshots/production/04-post-approval.png` |

---

## Architecture at a glance

```
                    ┌──────────────────────────── Browser (Vercel) ───────────────────────────┐
                    │  Next.js 15 · React 19 · TanStack Query · Tailwind                       │
                    │  dashboard · runs table · trace viewer · reasoning + assistant panels    │
                    │  telemetry store  ·  dev observability panel                             │
                    └───────────────────────────────┬──────────────────────────────────────────┘
                                                     │  HTTPS  (X-Request-ID echoed both ways)
                                                     ▼
                    ┌──────────────────────────── Backend (Render / Railway) ─────────────────┐
                    │  FastAPI · Pydantic v2                                                   │
                    │  RequestContextMiddleware  →  correlation id + timing + structured log   │
                    │                                                                          │
                    │  ┌── Pure compute core (no ORM) ──┐   ┌── Persistence at the edge ──┐    │
                    │  │ extraction · schema validation │   │ runs · validation logs ·    │    │
                    │  │ clinical rules · confidence ·  │──▶│ review items (single txn)   │    │
                    │  │ routing · reasoning · assistant│   └──────────────┬──────────────┘    │
                    │  └────────────────────────────────┘                  ▼                   │
                    │                                          SQLite (demo) / Postgres (prod) │
                    │  /health  /ready  probes                 Alembic migrations              │
                    └──────────────────────────────────────────────────────────────────────────┘
```

**Principles:** pure compute core with persistence only at the API boundary;
stable typed contracts (Pydantic read-models ↔ TypeScript types); dialect-portable
models so the same code runs on SQLite and Postgres; one shared `ROUTING_SERIES`
config so the donut and trend can never drift.

---

## Flow: review → reasoning → assistant → decision

```
  needs_review run
        │
        ▼
  ┌─────────────────┐   deterministic, model never narrates itself
  │ REASONING PANEL │   confidence meter · clinical policy violations ·
  │                 │   step-by-step decision path · reviewer-notes audit
  └────────┬────────┘
           │  operator wants a second read
           ▼
  ┌─────────────────┐   POST /api/runs/{id}/analyze  (advisory only, no mutation)
  │  AI ASSISTANT   │   content risks · diff risks · synthetic confidence
  │                 │   outcome:  stable  |  risk_alert
  └────────┬────────┘
           │  operator decides (may edit first)
           ▼
  ┌─────────────────┐   approve / reject  (409 if already decided — immutable)
  │  HUMAN DECISION │   edited approval preserves the original model output
  └────────┬────────┘
           ▼
  reviewed / rejected  →  dashboard updates via cache invalidation
                          every step emits a correlated, safe telemetry event
```

The human is always the decider. The assistant and reasoning panel *inform*; they
never approve, reject, or persist anything.

---

## Processing pipeline (extraction → storage)

```
transcript
   │
   ▼
1. AI extraction (OpenAI GPT-4o-mini or local Ollama)  ── provider abstraction
2. schema validation        (Pydantic v2)
3. clinical validation      (deterministic rule engine, local)
4. retry once if validation failed
5. derived confidence score (base 1.0 − capped penalties, clamped [0,1])
6. routing:  ≥0.85 & no critical → auto-save · 0.50–0.84 or critical → review · <0.50 → reject
7. persist the complete trace (run + issues + review item)
```

Statuses: `auto_saved` · `needs_review` · `reviewed` · `rejected` · `failed`.

---

## Quality gates (CI)

A single GitHub Actions workflow enforces the same checks used locally — no
Docker, no hosted database:

| Job | Runs | Blocking |
|---|---|---|
| **Frontend** | `npm run ci:frontend` → typecheck + Vitest + production build | ✅ |
| **Backend** | `uv run pytest` (117 tests) | ✅ |
| **E2E** | Playwright happy path + secondary flows (isolated seeded backend + prod build) | ✅ |
| **Screenshots** | `npm run e2e:screens` uploaded as an artifact (main / manual) | ⬜ |
| **Deploy** | manual `workflow_dispatch` only — frontend → Vercel, backend → Render | ⬜ manual |

Local commands: `uv run pytest` · `npm run ci:frontend` · `npm run test:e2e`.

---

## Deploy

- Frontend → Vercel: [`DEPLOY_PRODUCTION_FRONTEND.md`](DEPLOY_PRODUCTION_FRONTEND.md)
- Backend → Render/Railway: [`DEPLOY_PRODUCTION_BACKEND.md`](DEPLOY_PRODUCTION_BACKEND.md)

First-load budgets: dashboard ≤ 135 kB, run-detail ≤ 140 kB. Health probes:
`/api/health` (liveness + DB) and `/api/ready` (DB + schema).

---

## Further reading

- [`../README.md`](../README.md) — features + local setup
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — components and entities
- [`ENGINEERING_DECISIONS.md`](ENGINEERING_DECISIONS.md) — the non-obvious tradeoffs
- [`AI_PIPELINE.md`](AI_PIPELINE.md) · [`API.md`](API.md) — pipeline and HTTP contracts
