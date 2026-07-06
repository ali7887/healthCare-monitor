# Release Notes — Demo-Hardening Release (July 2026)

**healthCare-monitor (CareTrace)** — structured clinical documentation
extraction with deterministic validation, derived confidence, routing, and
human review. Live at
[health-care-monitor-steel.vercel.app](https://health-care-monitor-steel.vercel.app)
(backend: `caretrace-backend.vercel.app`, Neon Postgres).

> Non-diagnostic by design: the system structures documentation and surfaces
> *potential inconsistencies* for human review. It does not diagnose,
> prescribe, or recommend treatment.

## What the platform does

Accepts a caregiver/nursing transcript, extracts a structured clinical note,
validates it deterministically (JSON schema + clinical plausibility rules,
with one retry), derives a confidence score from concrete validation
outcomes, and routes the run: **auto-save** (≥ 0.85, no critical issues),
**human review** (0.50–0.85, or any critical), or **reject** (< 0.50). Every
run — including failures — persists a complete audit trace.

## Key reliability mechanisms

- **Derived confidence, never self-reported.** The model is never asked how
  confident it is. The score starts at 1.0 and subtracts weighted penalties
  for issue severity, issue type, and retries; the full penalty breakdown is
  stored and shown, and it always sums exactly to the final score.
- **Deterministic validation.** The same note always produces the same issues;
  rules run locally, not in the model.
- **Traceability.** Transcript, raw model response, parsed output, issues,
  routing reason, confidence breakdown, and a stepwise decision path are
  stored per run and browsable in the Trace Viewer.
- **Human review with edited approvals.** A reviewer can approve, reject, or
  correct the note before approving; corrections are stored alongside the
  original, and decided runs are immutable (conflict-guarded).
- **Advisory AI second read.** The reviewer assistant flags potential clinical
  risks; it never decides or displays a self-reported confidence figure.
- **Operational hardening.** `X-Request-ID` correlation end-to-end, structured
  JSON logs with **no clinical text ever logged**, credential-sanitized error
  reporting, health/readiness probes with build fingerprint
  (`/api/health` → env, version, commit SHA, uptime), per-widget frontend
  error boundaries, CI gates (types, unit tests, build, E2E).

## Run it locally

```bash
# Backend — Python 3.13 + uv; SQLite by default, no API key needed
cd caretrace/backend
cp .env.example .env
uv sync && uv run python -m app.seed_demo
uv run uvicorn app.main:app --reload --port 8000

# Frontend — Node 20+
cd caretrace/frontend
cp .env.local.example .env.local
npm install && npm run dev        # http://localhost:3000
```

Verification: `uv run pytest` (120 tests) · `npm test -- --run` (49 tests) ·
`npm run typecheck` · `npm run build`. Operator runbook (deploy, seed,
rollback): `docs/GO_LIVE_VERCEL.md`. Security policy: `SECURITY.md`.

## 3-minute guided demo

1. **Dashboard (30 s).** Point at the KPI strip — one routing vocabulary
   everywhere (Auto-save / Human review / Reject). Donut and stacked-bar
   throughput show the same series; ~83% average derived confidence.
2. **A clean trace (45 s).** Open a recent auto-saved run. Show the verbatim
   transcript beside the extracted note, then the confidence breakdown:
   zero issues → zero penalties → 1.00, and the four-step decision path.
3. **A flagged run (60 s).** Open a *Human review* run (elevated blood
   pressure). Show the two clinical warnings, the penalties they contribute,
   and that the derived score lands in the review band — the routing reason
   says exactly why a human is in the loop.
4. **The review workspace (45 s).** On the pending run, run the advisory
   assistant (it flags, never decides), edit the note (e.g. correct a missing
   dose), approve with notes — then show the immutable audit trail: original
   output, reviewer's correction, and notes all preserved.
5. **Close (10 s).** The rejected run: a critical oxygen-saturation issue
   pushed the score below 0.50 — unsafe output never gets silently saved.

## Known limitations / next steps

- Demo dataset is seeded and deterministic; live extraction requires an
  OpenAI key (or local Ollama) and processes English transcripts only.
- No authentication/RBAC or multi-tenancy — deliberately out of MVP scope;
  required before any real-customer pilot.
- Evaluation endpoint reports fixed-dataset metrics; no continuous eval loop.
- Neon password rotation after any credential exposure is a manual runbook
  step (`SECURITY.md`); no automated secret rotation.
- Not a medical device; no clinical claims. A regulatory/compliance review
  (GDPR data-processing agreement, PHI storage location) is a prerequisite to
  processing real patient data.
