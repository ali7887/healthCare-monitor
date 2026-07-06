# GO_LIVE_VERCEL.md — Production Deployment Runbook

The definitive operator runbook for taking the `caretrace/backend` service live on
Vercel serverless with Neon Postgres, and wiring it to the production frontend at
`https://health-care-monitor-steel.vercel.app`. The database is already
provisioned (migrated to `0003_phase20`, seeded with 19 runs); every remaining
step happens in the Vercel dashboard or a terminal.

The backend production domain is `caretrace-backend.vercel.app` (project
`caretrace-backend`). Use that public domain for all verification — the scoped
`caretrace-backend-ali7887s-projects.vercel.app` domain sits behind Vercel SSO
deployment protection and redirects unauthenticated requests.

---

## 1. Backend project checklist (Vercel dashboard)

1. **Project creation** — Vercel → Add New → Project, import this repository as
   a **separate project** from the frontend.
2. **Root Directory:** `caretrace/backend`. Vercel then auto-detects
   `vercel.json` and the `api/index.py` function (zero-config `@vercel/python`;
   dependencies install from `pyproject.toml` + `uv.lock`).
3. **Framework Preset:** Other. No build or start command — do not add a
   legacy `builds` array to `vercel.json`.
4. **Environment variables** (Production scope), exactly as written:

   | Key | Value |
   |---|---|
   | `CARETRACE_ENV` | `production` |
   | `DATABASE_URL` | `postgresql+psycopg://neondb_owner:[PASSWORD]@ep-steep-voice-aih0p52m-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require` |
   | `CORS_ORIGINS` | `https://health-care-monitor-steel.vercel.app` |
   | `CORS_ORIGIN_REGEX` | `^https://health-care-monitor-[a-z0-9-]+\.vercel\.app$` |
   | `CARETRACE_DEMO_SEED` | `0` |

   Notes that prevent the most common failures:
   - `DATABASE_URL` uses the **pooled** host (`…-pooler…`) and the
     `postgresql+psycopg://` scheme — not `postgres://` or `postgresql://`.
   - `CORS_ORIGINS` is a plain comma-separated string. **No JSON brackets, no
     quotes, no trailing slash** — `["https://…"]` would be treated as a
     literal (never-matching) origin.
5. **Redeploy after saving.** Env vars are snapshotted **per deployment** — the
   backend reads them at runtime, but an existing deployment never picks up new
   values. Trigger a redeploy after any env change.

---

## 2. Post-deployment verification routine

Run from PowerShell with `curl.exe` (the bare `curl` alias is
`Invoke-WebRequest` and formats output differently).

```powershell
# 1. Fingerprint: which app is deployed?
curl.exe -i https://caretrace-backend.vercel.app/
# Expect: HTTP 404 with JSON body {"detail":"Not Found"}
#         → CareTrace's FastAPI app is live (it defines no root route).

# 2. Liveness + DB connectivity + build fingerprint
curl.exe -i https://caretrace-backend.vercel.app/api/health
# Expect: HTTP 200 {"status":"ok","service":"healthCare-monitor-backend",
#                   "env":"production","version":"0.1.0","build":"<short sha>",
#                   "uptime_s":…}
#         "build" is the deployed commit (from VERCEL_GIT_COMMIT_SHA) — use it
#         to confirm which commit is actually serving traffic.

# 3. Readiness: schema present, correct env
curl.exe -i https://caretrace-backend.vercel.app/api/ready
# Expect: HTTP 200, "env":"production",
#         "checks":{"database":true,"schema":true}

# 4. Data persistence (seeded dataset via the pooled connection)
curl.exe https://caretrace-backend.vercel.app/api/dashboard/stats
# Expect: HTTP 200 with "total_runs": 19
```

### Diagnostic map

| Symptom | Layer | Resolution |
|---|---|---|
| `/` shows an HTML "Vercel + FastAPI" sample page | Wrong app | The project is building Vercel's FastAPI template, not this repo — re-link the repository and set Root Directory to `caretrace/backend`. |
| Plain-text 404 with `X-Vercel-Error: NOT_FOUND` header | Platform routing | Vercel never reached the function — verify Root Directory and that `vercel.json` + `api/index.py` are in the deployed commit. |
| `X-Vercel-Error: DEPLOYMENT_NOT_FOUND` | Platform | The domain points at a deleted project/deployment — use the current project's domain. |
| JSON `{"detail":"Not Found"}` on `/api/health` | Application | App is live but routes missing from the build — confirm the deployed commit is `bb487d7` or later. |
| `/api/ready` → `"database": false` (503) | Database | Read the `diagnostics` object in the same response (below). |
| `diagnostics.db_backend` = `"sqlite"` (503) | Config | `DATABASE_URL` never reached the function — unset, typoed key, or saved to the wrong environment scope. Set it (Production scope) and redeploy. |
| `diagnostics.db_backend` = `"postgresql"` with `errors` (503) | Database | The app read `DATABASE_URL` but can't connect — check `db_host` in the response (should be the `…-pooler…` Neon host), the password, and `sslmode=require`. Bare `postgres://`/`postgresql://` schemes are auto-normalized to psycopg. |
| `/api/ready` → `"schema": false` (503) | Database | Connected, but tables missing — URL points at the wrong Neon branch/database (migrations ran on `neondb` @ `ep-steep-voice-aih0p52m`). |
| `/api/ready` → `"env": "dev"` | Config | `CARETRACE_ENV` unset or typoed (unknown values fall back to `dev`) — set it and redeploy. |
| Logs: `prepared statement "…" already exists` | Database (pooler) | Apply `connect_args={"prepare_threshold": None}` on the **non-SQLite** branch of `app/db/session.py`. `None` disables server-side prepared statements; do **not** use `0`, which prepares on first execution and makes it worse. Apply only if this error actually appears. |
| Browser CORS error (curl works) | CORS | `CORS_ORIGINS` must exactly equal the frontend origin — no trailing slash, no JSON array syntax. |

---

## 3. Frontend hookup

1. On the **frontend** Vercel project (`health-care-monitor`), set for
   Production:

   ```
   NEXT_PUBLIC_API_BASE_URL=https://caretrace-backend.vercel.app/api
   ```

   The `/api` suffix is required and there is no trailing slash. If the
   variable is missing, the build silently falls back to
   `http://localhost:8000/api` and every production API call fails.
2. **Redeploy the frontend.** `NEXT_PUBLIC_*` values are inlined into the JS
   bundle at build time — saving the variable does nothing until a fresh build
   runs.
3. **Browser validation** on
   `https://health-care-monitor-steel.vercel.app/dashboard`:
   - Network tab: requests go to `https://caretrace-backend.vercel.app/api/…` and carry
     an `X-Request-ID` response header.
   - Any `OPTIONS` preflight returns **200** (Starlette's CORSMiddleware
     replies 200, not 204) with an `Access-Control-Allow-Origin` header naming
     the frontend origin.
   - No CORS errors in the console; approving/rejecting a review item persists
     across a reload (round-trip to Neon).

---

## 4. Seeding / re-seeding the database

The seeded dataset is deterministic: fixed transcripts, notes, issues, and
confidence breakdowns; only the timestamps are relative to the moment the seed
runs (runs are spread over the previous 14 days so the throughput chart is
always populated). Re-run the seed after any `seed_demo.py` change.

**Local (SQLite — safe to run any time):**

```powershell
cd caretrace/backend
uv run python -m app.seed_demo          # reset + seed 19 runs
```

**Production (Neon):** use the **DIRECT** connection string (host *without*
`-pooler`) transiently — never store it, never use it as the runtime URL:

```powershell
cd caretrace/backend
$env:DATABASE_URL = "<DIRECT Neon URL>"   # paste from Neon console, direct host
uv run alembic upgrade head               # only if migrations changed
uv run python -m app.seed_demo            # deletes rows, re-seeds 19 runs
Remove-Item Env:DATABASE_URL
```

Expected output ends with `Seeded 19 demo runs (reset)` and the status counts
(11 auto_saved / 3 needs_review / 2 reviewed / 2 rejected / 1 failed). Verify
with `GET /api/dashboard/stats` → `"total_runs": 19`.

---

## 5. Rollback

Application rollback (bad deploy, either project):

1. Vercel dashboard → project → **Deployments** → pick the last known-good
   deployment → **⋯ → Promote to Production**. This is instant and does not
   rebuild.
2. Verify with §2 (backend) / §3.3 (frontend). `/api/health` → `build` should
   show the rolled-back commit SHA.
3. Revert or fix the offending commit on `main` before the next push, otherwise
   the next auto-deploy reintroduces it.

Data rollback (bad seed / accidental writes): re-run the seed (§4) — it resets
all rows deterministically. For anything beyond demo data, use a Neon
point-in-time branch restore.

---

## 6. Post-go-live security wrap-up

The Neon password was exposed during setup and **must be rotated**:

1. Rotate the role password in the Neon console (`neondb_owner`).
2. Update `DATABASE_URL` in the Vercel backend project with the new password
   (same pooled host, same query params).
3. Redeploy the backend.
4. Re-run the verification routine (§2) end-to-end.

Rotation steps in detail (incl. least-privilege guidance): see `SECURITY.md`
at the repository root.
