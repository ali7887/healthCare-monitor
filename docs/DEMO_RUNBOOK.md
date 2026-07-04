# Demo Runbook

A tight, repeatable script for showing healthCare-monitor live (interview, portfolio review, or stakeholder demo). Budget ~8–10 minutes. The framing throughout: **this system treats LLM output as untrusted until deterministic checks pass, and keeps a full audit trace of every decision.**

---

## 0. One-time setup (before the demo)

```bash
# Terminal 1 — backend
cd caretrace/backend
uv sync
uv run python -m app.seed_demo          # loads the demo dataset
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd caretrace/frontend
npm install
npm run dev
```

Confirm the API status pill in the header reads **API online**, then open <http://localhost:3000/dashboard>.

No API key, Docker, or Postgres is needed for the seeded demo.

---

## 1. Open on the dashboard (the "what" in one screen) — ~1 min

Point out, top to bottom:

- **KPI strip** — total runs, auto-saved, needs-review, rejected, average confidence.
- **Routing distribution donut** — how outputs were routed. Emphasize the split: most auto-saved, a meaningful slice sent to humans, a few rejected. *"Nothing here is faked — these are real counts from processed runs."*
- **Throughput trend** — runs per day over the last two weeks, stacked by routing outcome.

Key line: *"The donut and the trend read from two different endpoints but share one routing-series config, so they can never disagree — there's a regression test that enforces it."*

## 2. Runs table — filtering and density — ~1 min

Go to **Runs**. Show:

- Server-side pagination + filter by routing decision (Auto-save / Human review / Reject).
- Each row: short id, provider, routing badge, status badge, confidence, latency, age.

*"Every processed transcript lands here regardless of outcome — including failures — because traceability is the point."*

## 3. Trace viewer — the audit trail — ~2 min

Open any run (e.g. an auto-saved one). Walk the three columns:

- **Metadata** — provider, latency, cost, retry count, timestamps.
- **Structured output** — the extracted clinical note.
- **Decision panel** — routing decision, human-readable routing reason, and the **confidence breakdown** (base score minus each penalty).

Key line: *"We never ask the model how confident it is. Confidence is derived locally from concrete validation outcomes — that number is explainable and reproducible."*

## 4. Human review — approve / reject — ~2 min

Open a **needs-review** run (find one via the "Human review" filter or the queue). In the review panel:

1. Read the **validation issue** that flagged it (e.g. blood pressure above expected range).
2. Add an optional reviewer note.
3. **Reject** one to show it route out, or **Approve** to accept the documentation.
4. Return to the dashboard — the KPI strip and charts have already updated (React Query cache invalidation, no manual refresh).

## 5. Edited approval — the reliability highlight — ~2 min

Open a needs-review run and tick **"Edit output before approving"**:

- The JSON editor opens with the model's output. Make a correction (e.g. fill in a missing medication dose).
- Note the client-side JSON validation: malformed JSON or a non-object is blocked *before* any request, with an inline alert.
- Approve. The corrected note becomes the run's `final_output`.

Key line: *"The reviewer's correction is stored as `edited_output`; the original model response and parsed output are never overwritten. You can always see what the model said versus what the human accepted."*

Then, optionally, try to act on that run again to show the **409 conflict guard**: a decided review is immutable — re-approving/re-rejecting is rejected, not silently re-applied.

## 6. Observability (developer aside) — optional ~1 min

In dev mode a small **debug panel** pins to the corner exposing the raw time-series payload, the routing-series mapping, and live query states. *"This is dev-only — it's tree-shaken out of production builds — but it makes drift between the charts and the data obvious while building."*

Mention performance: Recharts is dynamically imported, so the dashboard's initial JS is ~130 kB instead of ~238 kB.

---

## Recovery — if local data gets out of sync

| Symptom | Fix |
|--------|-----|
| Charts empty / weird distribution | Re-seed: `cd caretrace/backend && uv run python -m app.seed_demo` (resets to the known dataset) |
| Want to append without wiping | `uv run python -m app.seed_demo --keep` |
| Header shows **API unreachable** | Confirm the backend is running on `:8000`; check `NEXT_PUBLIC_API_BASE_URL` in `caretrace/frontend/.env.local` |
| Browser console shows CORS errors | Ensure your frontend origin is listed in `CORS_ORIGINS` (backend `.env`); default allows `http://localhost:3000` |
| Totally fresh start | Stop the backend, delete `caretrace/backend/caretrace_demo.db`, re-run the seed (tables auto-create) |

---

## End-to-end tests & screenshots

The demo path above is protected by a small Playwright suite, and the same
tooling generates the portfolio screenshots. **Prerequisites:** Node, Python +
`uv`, and a system **Google Chrome** (Playwright uses it via `channel: "chrome"`,
so no browser binary is downloaded).

**No manual startup is needed** — Playwright's `webServer` launches everything:

- an **isolated backend** on its own SQLite file (`caretrace_e2e.db`) that
  **re-seeds on every start**, so E2E is deterministic and never touches your
  demo database (`caretrace_demo.db`);
- a **production frontend build** (so behavior — and screenshots — match what a
  real user sees, with the dev debug overlay absent).

From `caretrace/frontend`:

```bash
npm run test:e2e          # run the demo-path + secondary E2E tests (headless)
npm run test:e2e:headed   # same, with a visible browser (nice for live demos)
npm run e2e:screens       # regenerate docs/screenshots/ from seeded data
```

What the suite covers:

- **Happy path** — open the dashboard (KPI strip, donut, trend all render) →
  open a flagged run → edit the JSON output → approve → confirm the decision
  persisted (`reviewed`, dropped from the queue) and the dashboard still renders.
- **Reject flow** — reject a flagged run and confirm it persists as `rejected`.
- **Already-decided run** — a resolved run shows its outcome and offers **no**
  review actions (the reachable UI face of the backend's immutable-decision guard).

Screenshots are written to [`docs/screenshots/`](screenshots/) — see its README
for the file map and when to refresh. No seed reset is required by hand; each
run reseeds its isolated database automatically.

## CI quality gate

The same commands run in CI on every push and pull request via a single GitHub
Actions workflow ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

- **Blocking:** frontend type-check + unit tests + production build (`npm run ci:frontend`),
  backend tests (`uv run pytest`), and the Playwright E2E happy path (`npm run ci:e2e`,
  gated behind the fast checks).
- **Non-blocking:** screenshot capture runs on `main` / manual dispatch and uploads the
  PNGs as an artifact (kept off PRs to stay fast).
- **Artifacts:** the Playwright HTML report is uploaded every E2E run; failure traces on
  failure. CI installs the real Chrome channel to match the local `channel: "chrome"` config.

See the README's "Continuous integration" section for the full table.

---

## Talking points cheat-sheet

- **"Deterministic validation over model self-trust"** — rules run locally; confidence is derived, not asked for.
- **"Traceability over black-box"** — raw response, parsed output, issues, routing reason, and confidence breakdown are all persisted per run.
- **"Human review over unsafe automation"** — critical issues force review regardless of score; edited approvals preserve the original.
- **"Tested and hardened"** — 86 backend + 25 frontend tests, a Playwright demo-path E2E suite, and a GitHub Actions quality gate; plus per-widget error boundaries, an immutable-decision 409 guard, and lazy-loaded charts.
