# Deploy the frontend (Vercel)

How to put the healthCare-monitor frontend online on **Vercel**, pointed at a
deployed backend (see [`DEPLOY_PRODUCTION_BACKEND.md`](DEPLOY_PRODUCTION_BACKEND.md)).

> **Scope note.** The repository is deploy-ready. The only steps that require
> *your* account are importing the project and setting environment variables in
> the Vercel dashboard — there is no code change to make.

---

## Prerequisites

- The backend is already deployed and its `/api/health` returns `ok`.
- You know the backend's public API base URL, including the `/api` suffix, e.g.
  `https://caretrace-backend.onrender.com/api`.

---

## 1. Import the project

1. **Vercel → Add New → Project**, import this repository.
2. **Root Directory:** `caretrace/frontend`.
3. **Framework Preset:** Next.js (auto-detected).
4. Build & Output settings: leave the defaults (`next build`).

---

## 2. Environment variables

Set these in **Project → Settings → Environment Variables** (Production scope).
A template lives at
[`caretrace/frontend/.env.production.example`](../caretrace/frontend/.env.production.example).

| Variable | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://<your-backend-host>/api` | **Include the `/api` suffix.** Inlined into the bundle at build time. |
| `NEXT_PUBLIC_OBSERVABILITY` | `0` | Keep `0` in production. Set `1` only to opt in to the dev observability panel on a deployed instance for debugging. |

> **Why not commit `.env.production`?** Next.js auto-loads `.env.production` at
> build time and inlines every `NEXT_PUBLIC_*` value, which would bake a
> placeholder URL into the bundle. Setting the values in Vercel's dashboard is
> the correct path — hence the committed file is `.env.production.example`, a
> template only.

Because `NEXT_PUBLIC_API_BASE_URL` is inlined at build time, **changing it
requires a redeploy** (not just a restart).

---

## 3. Deploy and connect to the backend

1. Deploy. Vercel builds with the env vars above.
2. Copy the resulting Vercel domain (e.g. `https://caretrace.vercel.app`).
3. Back on the backend host, set `CORS_ORIGINS` to that exact domain and
   redeploy the backend (see the backend guide). The API sends
   `allow_credentials=true`, so the origin must be listed explicitly — no `*`.

---

## 4. Verify

1. Open `https://<your-vercel-domain>/dashboard` — the KPI strip, routing donut,
   and throughput trend should populate from the seeded backend.
2. Open any run → the trace viewer, reasoning panel, and AI assistant panel work.
3. In the browser dev tools **Network** tab, a request to the backend should
   carry an `X-Request-ID` response header — the same id appears in the backend
   logs for that request.

If the dashboard is empty or requests fail with CORS errors, the two usual
causes are: `NEXT_PUBLIC_API_BASE_URL` missing the `/api` suffix, or the backend
`CORS_ORIGINS` not listing the exact Vercel domain.

---

## 5. Enabling the observability panel on a deployed instance

The dev observability panel is hidden in production by default. To turn it on for
debugging a deployed instance, set `NEXT_PUBLIC_OBSERVABILITY=1` and redeploy. It
renders bottom-left and shows recent request ids, API latencies, the last
assistant result, and the telemetry event stream — all client-side, no data
leaves the browser.

---

## Bundle size budget

Keep the production bundles within budget (verified by `npm run build`):

| Route | First Load JS | Budget |
|---|---|---|
| `/dashboard` | ~131 kB | ≤ 135 kB |
| `/dashboard/runs/[id]` | ~134 kB | ≤ 140 kB |

Recharts is dynamically imported so it stays off the initial dashboard payload.
Do not add client dependencies without re-checking these numbers.
