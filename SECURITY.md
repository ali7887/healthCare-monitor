# Security

Operational security policy for healthCare-monitor (CareTrace). Scope: secrets
handling, credential rotation, deployment configuration, and data-safety rules
for logs. This is an MVP policy — deliberately short and enforceable.

## Secrets policy

- **Never commit secrets.** Only `*.example` environment templates are tracked;
  real values live in local `.env` / `.env.local` files (git-ignored at the
  root, backend, and frontend levels) and in the Vercel project environment.
- **Never print full `DATABASE_URL`** (or any URL containing `user:password@`)
  in logs, shell output, docs, or chat. Backend error paths sanitize URLs to
  `://***@` before logging (`app/api/routes/system.py`).
- Key material (`*.pem`, `*.key`) is git-ignored and must never be tracked.
- A pre-commit guard blocks env files and common credential patterns — enable
  it once per clone:

  ```bash
  git config core.hooksPath .githooks
  ```

## Rotating the Neon database password

Rotate immediately if a credential is ever pasted into a chat, ticket, log, or
screen share.

1. Neon console → project → **Roles** → `neondb_owner` → **Reset password**.
   Copy the new connection strings (pooled *and* direct).
2. Vercel → backend project (`caretrace-backend`) → **Settings → Environment
   Variables** → replace `DATABASE_URL` with the new **pooled** URL
   (host contains `-pooler`). Runtime traffic must always use the pooled host.
3. Redeploy the backend (Vercel → Deployments → Redeploy, or push to `main`),
   then verify:

   ```bash
   curl https://caretrace-backend.vercel.app/api/health
   curl https://caretrace-backend.vercel.app/api/ready
   ```

4. Update any local `.env` that used the old password. The **direct** URL
   (host without `-pooler`) is used only transiently for migrations/seeding and
   should not be stored anywhere persistent.

## Updating Vercel environment variables

1. Vercel dashboard → project → **Settings → Environment Variables**.
2. Backend variables (`DATABASE_URL`, `CORS_ORIGINS`, `CARETRACE_ENV`, …) take
   effect on the **next deployment** — redeploy after changing them.
3. Frontend `NEXT_PUBLIC_*` variables are **inlined at build time** — changing
   them always requires a rebuild/redeploy, and they are visible to browsers by
   design, so they must never contain secrets.

## Least privilege

- The OpenAI key (if configured) needs model-inference access only — no admin
  or billing scopes.
- Prefer separate Neon roles per environment; the demo deployment needs a
  single read/write role on one database, nothing broader. Use Neon's
  IP-allowlist / protected-branch features if the plan allows.
- CI deploy jobs are manual-only (`workflow_dispatch`) and read repository
  secrets scoped to the `production` environment.

## Data safety in logs

Structured logs and telemetry record **safe metadata only**: ids, statuses,
counts, durations, outcome categories (`app/core/telemetry.py`). Raw clinical
text — transcripts, extracted notes, model responses — is stored in the
database as part of the audit trace but is **never written to logs**. Database
errors are logged as exception class + credential-sanitized first line only.

## Reporting

This is a portfolio/demo project. Report suspected issues by opening a GitHub
issue (omit any sensitive values) or contacting the repository owner directly.
