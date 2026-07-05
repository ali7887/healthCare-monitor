# Deploy the backend (Render / Railway)

How to put the healthCare-monitor backend online on a managed host. It targets
**Render** (Blueprint or manual Web Service) with notes for **Railway**; both
run the same start command. No Docker, no Kubernetes — just a Python web service.

> **Scope note.** This guide is written so you can deploy in a few minutes. The
> repository ships everything needed (start script, config, health checks); the
> only steps that require *your* account are creating the service and setting
> environment variables in the host's dashboard.

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
