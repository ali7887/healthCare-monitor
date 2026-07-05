# Deploy the backend (Vercel serverless · Render / Railway)

How to put the healthCare-monitor backend online. The **active deployment target
is Vercel serverless** (§ below); **Render/Railway** (long-running server) remain
supported as an alternative. No Docker, no Kubernetes.

> **Scope note.** This guide is written so you can deploy in a few minutes. The
> repository ships everything needed (entrypoint, `vercel.json`, `requirements.txt`,
> config, health checks); the only steps that require *your* account are creating
> the project and setting environment variables in the host's dashboard.

---

## Vercel serverless (active target)

The backend runs as a single **Python Serverless Function** wrapping the FastAPI
ASGI app — Vercel invokes the app directly, so no uvicorn/gunicorn process runs.

### Files (shipped in `caretrace/backend/`)

| File | Role |
|---|---|
| [`api/index.py`](../caretrace/backend/api/index.py) | Serverless entrypoint; exposes the module-level ASGI `app` (`from app.main import app`). |
| [`vercel.json`](../caretrace/backend/vercel.json) | Rewrites `/(.*)` → `/api/index`, so every path reaches the function. The app keeps its own `/api` prefix, so `/api/health` resolves unchanged. |
| [`requirements.txt`](../caretrace/backend/requirements.txt) | Runtime deps for `@vercel/python` (no uvicorn/gunicorn/alembic — not needed at runtime). |
| [`.vercelignore`](../caretrace/backend/.vercelignore) | Keeps local SQLite files, `.venv`, and tests out of the bundle. |

### Create the project

1. **Vercel → Add New → Project**, import this repository (a **separate** Vercel
   project from the frontend).
2. **Root Directory:** `caretrace/backend` — Vercel then finds `vercel.json`,
   `requirements.txt`, and the `api/` function automatically.
3. **Framework Preset:** Other. No build command is needed; `@vercel/python`
   installs `requirements.txt` and builds the function.
4. Set the environment variables (table below), then deploy. The active domain in
   this project is `fastapi-blush-two.vercel.app`.

### Environment variables (Vercel backend project)

| Variable | Value | Notes |
|---|---|---|
| `CARETRACE_ENV` | `production` | Production logging profile; no boot seeding. |
| `DATABASE_URL` | `postgresql+psycopg://USER:PASS@HOST/DB` | **Required** — see the database note; use a **pooled** endpoint. |
| `CORS_ORIGINS` | `https://<your-frontend>.vercel.app` | Your frontend production domain (comma-separated for several). |
| `CORS_ORIGIN_REGEX` | `^https://<frontend-project>-[a-z0-9-]+\.vercel\.app$` | *Optional* — allows that project's preview deployments. |
| `CARETRACE_LOG_LEVEL` | `INFO` | Structured log level. |
| `OPENAI_API_KEY` | *(only for live extraction)* | Not needed for the seeded demo/dashboard. |

> Do **not** set `CARETRACE_DEMO_SEED` on Vercel (see seeding note). `PORT`,
> `WEB_CONCURRENCY`, and `start_production.sh` are **not** used on Vercel — those
> belong to the Render/Railway path.

### Database & migrations on serverless — important

Vercel's filesystem is **read-only and ephemeral** (only `/tmp`, per-invocation,
not shared across instances). Therefore:

- **SQLite is not viable** on Vercel — writes (review approve/reject) would not
  persist or be shared. **Use an external Postgres** (Neon, Supabase, or Vercel
  Postgres). Because `DATABASE_URL` is non-SQLite, the app skips `create_all` and
  treats the schema as Alembic-managed.
- **Use a pooled connection string.** Serverless spins up many short-lived
  instances; a direct Postgres connection exhausts server slots. Point
  `DATABASE_URL` at the provider's pooler (e.g. Neon's `-pooler` host, Supabase's
  transaction pooler on port `6543`).
- **Do not run migrations on cold start.** Cold starts are frequent, concurrent,
  and time-limited — running `alembic upgrade head` there risks lock contention,
  partial migrations, and timeouts. The app already never migrates on boot. Run
  migrations **externally, once per schema change**, from your machine or CI:
  ```bash
  cd caretrace/backend
  DATABASE_URL="postgresql+psycopg://…prod…" uv run alembic upgrade head
  ```
- **Seed once, externally.** Leave `CARETRACE_DEMO_SEED` unset on Vercel (a
  boot-time seed could race between two cold starts). Seed the demo dataset once
  against the production Postgres from your machine:
  ```bash
  cd caretrace/backend
  DATABASE_URL="postgresql+psycopg://…prod…" uv run python -m app.seed_demo
  ```
  (The lifespan seed remains guarded — only-if-empty and wrapped so a race can
  never crash a boot — but running it once externally is the deterministic path.)

### Verify

```bash
curl https://fastapi-blush-two.vercel.app/api/health
# {"status":"ok","service":"healthCare-monitor-backend"}
curl https://fastapi-blush-two.vercel.app/api/ready
# {"status":"ready", ... ,"checks":{"database":true,"schema":true}}
```

Then set the frontend's `NEXT_PUBLIC_API_BASE_URL` to
`https://fastapi-blush-two.vercel.app/api` and redeploy the frontend (see
[`DEPLOY_PRODUCTION_FRONTEND.md`](DEPLOY_PRODUCTION_FRONTEND.md)).

---

## Alternative: Render / Railway (long-running server)

Use this if you prefer a persistent process (`start_production.sh` + uvicorn)
instead of serverless. It targets **Render** (Blueprint or manual Web Service)
with notes for **Railway**; both run the same start command.

---

## What gets deployed

- **App:** `app.main:app` (FastAPI), launched by
  [`caretrace/backend/start_production.sh`](../caretrace/backend/start_production.sh).
- **Database:** SQLite by default (fine for a demo), or an external Postgres
  via `DATABASE_URL` for a production-like setup. The models are dialect-portable,
  so the same code runs on either.
- **Migrations:** on a non-SQLite `DATABASE_URL`, the start script runs
  `alembic upgrade head` before launching. On SQLite, tables auto-create on boot.

---

## Environment variables

| Variable | Example | Purpose |
|---|---|---|
| `CARETRACE_ENV` | `production` or `demo` | Deployment mode (logging profile, boot seeding). |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host/db` | External database. Omit to use bundled SQLite. |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Comma-separated allowed browser origins (your Vercel domain). |
| `CARETRACE_LOG_LEVEL` | `INFO` | Structured log level. |
| `CARETRACE_DEMO_SEED` | `1` | **Demo only.** Seeds the deterministic dataset if the DB is empty. Leave unset in production. |
| `WEB_CONCURRENCY` | `2` | uvicorn worker count (scale to the host's CPU). |
| `PORT` | provided by host | Bind port — Render/Railway inject this automatically. |

> **CORS:** set `CORS_ORIGINS` to your exact Vercel production domain (and any
> preview domains you want to allow). Do **not** use `*` — the API sends
> `allow_credentials=true`, so the origin list must be explicit.

---

## Render — manual Web Service (quickest)

1. **New → Web Service**, connect this repo.
2. **Root Directory:** `caretrace/backend`
3. **Runtime:** Python 3.
4. **Build Command:**
   ```bash
   pip install uv && uv sync --frozen
   ```
   (Or `pip install -r requirements.txt` if you export one; `uv sync` is the
   supported path.)
5. **Start Command:**
   ```bash
   bash start_production.sh
   ```
6. **Environment:** add the variables from the table above. For a public demo
   with zero external infra, set only `CARETRACE_ENV=demo`,
   `CARETRACE_DEMO_SEED=1`, and `CORS_ORIGINS=<your Vercel URL>`.
7. **Create Web Service.** First boot: SQLite tables auto-create and (in demo
   mode) the dataset seeds itself.

### Render — with Postgres

1. Create a **Render Postgres** instance; copy its **Internal Database URL**.
2. Set `DATABASE_URL` to that value and `CARETRACE_ENV=production`.
3. Deploy. The start script runs `alembic upgrade head` automatically before
   launch. Leave `CARETRACE_DEMO_SEED` unset so production data is never touched.

---

## Railway

1. **New Project → Deploy from GitHub repo.**
2. Set the service **Root Directory** to `caretrace/backend`.
3. **Start command:** `bash start_production.sh`.
4. Add the same environment variables. Railway also injects `PORT`.
5. (Optional) add a Railway Postgres plugin and set `DATABASE_URL` from it.

---

## Verify the deployment

Once live, both platform probes should pass:

```bash
curl https://<your-backend-host>/api/health
# {"status":"ok","service":"healthCare-monitor-backend"}

curl https://<your-backend-host>/api/ready
# {"status":"ready","service":"...","env":"demo","checks":{"database":true,"schema":true}}
```

- `/health` — liveness + database connectivity (returns **503** if the DB is
  unreachable). Use this as the host's **health check path**.
- `/ready` — readiness: database reachable **and** core schema present (returns
  **503**, naming the failing probe, until migrations/seed have run).

Point your host's health check at `/api/health`.

---

## Logs & request correlation

Logs are single-line structured JSON on stdout — the host's log viewer captures
them with no shipper. Every request carries a correlation id:

```json
{"ts":"2026-07-05T12:00:00Z","level":"INFO","logger":"caretrace.http","message":"http_request","request_id":"a1b2c3...","event":"http_request","method":"POST","path":"/api/runs/{id}/analyze","status_code":200,"duration_ms":22.5}
```

The `request_id` is generated per request (or preserved from an incoming
`X-Request-ID`) and echoed on the response, so a UI observation can be traced to
the exact backend log line. See
[`ENGINEERING_DECISIONS.md`](ENGINEERING_DECISIONS.md#11-observability-is-thin-local-first-and-privacy-safe).

Log retention is whatever the host provides (Render/Railway retain recent
stdout); there is no external aggregation by design.

---

## Reset a demo instance

A demo database can be reset to the canonical dataset by redeploying with
`CARETRACE_DEMO_SEED=1` against an empty database, or by running the seed
command in the host shell:

```bash
uv run python -m app.seed_demo   # reset + seed
```
