# DEPLOYMENT.md

## Deployment goal
Support simple MVP deployment for demo and portfolio use.

## Local stack
- frontend: Next.js
- backend: FastAPI
- database: Postgres via Docker Compose

## Environment variables
Root:
- shared URLs if needed

Backend:
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OLLAMA_BASE_URL` (optional)
- `DEFAULT_PROVIDER` — `openai` or `ollama`
- `DEFAULT_MODEL` — e.g. `gpt-4o-mini` or `qwen2.5`

Frontend:
- `NEXT_PUBLIC_API_BASE_URL` — e.g. `http://localhost:8000/api`

## Local startup

### Database
```bash
docker compose up -d
```

### Backend
```bash
cd backend
cp .env.example .env   # set DATABASE_URL and OPENAI_API_KEY
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
```

### Verify
- Backend health: `http://localhost:8000/api/health` returns `{ "status": "ok" }`
- Frontend: `http://localhost:3000`

## Optional local provider (Ollama)
```bash
ollama pull qwen2.5
ollama serve
```
Set `OLLAMA_BASE_URL` and select the `ollama` provider in the Process console.

## Database migrations
- Apply migrations before first run.
- Keep a single, linear migration history for the MVP.
- Migrations are additive; avoid destructive changes to trace tables.

## Demo checklist
1. Start Postgres, backend, and frontend.
2. Confirm `/api/health` is green.
3. Load a sample from `examples/` in the Process console.
4. Process with each provider to compare behavior.
5. Show an auto-saved run and a `needs_review` run.
6. Open a trace to demonstrate full auditability.
7. Show the evaluation dashboard.

## Production notes (out of MVP scope)
The MVP targets local and demo environments only. Hardening such as TLS,
managed Postgres, secrets management, and horizontal scaling is intentionally
deferred and not part of this prototype.
