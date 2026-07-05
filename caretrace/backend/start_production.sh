#!/usr/bin/env bash
#
# Production startup script for the healthCare-monitor backend.
#
# Used as the Render/Railway "start command". It (1) applies database
# migrations when running against a real database, (2) optionally seeds the
# deterministic demo dataset, and (3) launches uvicorn with production-minded
# worker/timeout settings.
#
# Environment (see app/core/config.py):
#   CARETRACE_ENV=production|demo       deployment mode
#   DATABASE_URL=postgresql://...       external database (Alembic-managed)
#   CARETRACE_DEMO_SEED=1               seed demo data on boot if DB is empty
#   CARETRACE_LOG_LEVEL=INFO            structured log level
#   PORT=8000                           port to bind (host provides this)
#   WEB_CONCURRENCY=2                   number of uvicorn workers
#
# Log retention is handled by the platform (Render/Railway capture stdout);
# logs are structured single-line JSON, so the host's log viewer is grep-able
# with no extra shipping. See docs/DEPLOY_PRODUCTION_BACKEND.md.

set -euo pipefail

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
DATABASE_URL="${DATABASE_URL:-sqlite:///./caretrace_demo.db}"

# 1. Migrations. On a real (non-SQLite) database, Alembic owns the schema.
#    SQLite creates tables on startup (see app.main lifespan), so skip there.
case "$DATABASE_URL" in
  sqlite*) echo "[start] SQLite detected — tables auto-create on startup; skipping migrations." ;;
  *)       echo "[start] Applying database migrations (alembic upgrade head)..."
           alembic upgrade head ;;
esac

# 2. Optional deterministic demo seed. The app also self-seeds on boot when
#    CARETRACE_DEMO_SEED=1 and the DB is empty; this is the explicit equivalent
#    for hosts that prefer an init step. Safe to leave unset in production.
if [ "${CARETRACE_DEMO_SEED:-0}" = "1" ]; then
  echo "[start] CARETRACE_DEMO_SEED=1 — demo dataset will be loaded if the database is empty."
fi

# 3. Launch. --timeout-keep-alive guards against slow/stuck clients holding a
#    worker; --workers scales with the host's CPU allocation.
echo "[start] Launching uvicorn on 0.0.0.0:${PORT} with ${WEB_CONCURRENCY} worker(s)..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --timeout-keep-alive 30 \
  --proxy-headers \
  --forwarded-allow-ips "*"
