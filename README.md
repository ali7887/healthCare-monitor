# CareTrace

Reliable AI-assisted clinical documentation with validation, traceability, and human review.

## Overview
CareTrace is a lean healthcare AI reliability prototype that converts unstructured nursing or caregiver transcripts into structured clinical notes, validates outputs using deterministic rules, retries once for self-correction, calculates a derived confidence score, and routes uncertain results to human review.

## Why this project exists
Clinical and nursing documentation is often recorded as free text. Free text is difficult to search, standardize, audit, and validate. Naive LLM extraction is insufficient in healthcare-sensitive contexts because outputs may be malformed, incomplete, or clinically inconsistent.

CareTrace focuses on reliability rather than novelty:
- deterministic validation
- traceability
- human-in-the-loop review
- evaluation and model comparison

## Core capabilities
- Transcript input and example loader
- Provider switcher: OpenAI GPT-4o-mini and local Qwen2.5 via Ollama
- Structured clinical extraction
- Pydantic schema validation
- Deterministic clinical validation rules
- One-step self-correction retry loop
- Derived confidence score
- Auto-save vs human review routing
- Review queue with approve/edit/reject
- Full run trace storage
- Evaluation dashboard

## Safety and scope
CareTrace does **not** provide diagnosis, treatment recommendations, or clinical decision-making.  
It only structures documentation and flags potential inconsistencies for human review.

This MVP intentionally excludes:
- authentication
- RBAC
- voice streaming
- RAG / vector search
- real EHR integration
- notifications
- realtime collaboration
- multi-tenancy

## High-level architecture
Frontend: Next.js  
Backend: FastAPI  
Validation: Pydantic + deterministic rule engine  
Storage: Postgres  
LLM orchestration: provider abstraction with trace capture

Pipeline:
1. Transcript input
2. AI extraction
3. Schema validation
4. Clinical validation
5. Retry once if needed
6. Confidence scoring
7. Auto-save or route to review
8. Trace persistence
9. Dashboard and evaluation

## Repository structure
See `ARCHITECTURE.md` and `docs/API.md` for detailed system contracts.

## Local development
### Prerequisites
- Node.js
- Python 3.11+
- uv
- Docker / Docker Compose
- Postgres
- OpenAI API key for GPT-4o-mini
- Optional: Ollama for local Qwen2.5

### Environment
Copy:
- `.env.example` → `.env`
- `backend/.env.example` → `backend/.env`

### Run services
```bash
# Start Postgres
docker compose up -d

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Default local endpoints:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000/api`
- Health check: `http://localhost:8000/api/health`

## Documentation
- `CLAUDE.md` — working rules and project constraints for Claude Code
- `ARCHITECTURE.md` — components, pipeline, and entities
- `DECISIONS.md` — key design decisions and rationale
- `TASKS.md` — phased implementation plan
- `docs/PRD.md` — product requirements
- `docs/AI_PIPELINE.md` — end-to-end AI processing pipeline
- `docs/API.md` — HTTP API contracts
- `docs/DESIGN_SYSTEM.md` — Clinical Clarity design system
- `docs/TESTING.md` — testing strategy and priorities
- `docs/DEPLOYMENT.md` — local and demo deployment

## Status
This repository is currently in documentation-first setup. Application code is implemented in later phases; see `TASKS.md`.
