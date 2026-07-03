# healthcare-monitor Project Status

Last updated after: Phase 4 — Extraction Schemas  
Current next phase: Phase 5 — Deterministic Validation Engine

---

## Product Identity

Project name: healthcare-monitor

Subtitle:

Reliable AI-assisted clinical documentation with validation, traceability, and human review.

One-liner:

healthcare-monitor converts unstructured nursing/care transcripts into structured clinical notes, validates them with deterministic safety rules, and routes uncertain outputs to human review.

README / Demo slogan:

Reliable clinical documentation through deterministic AI outputs, validation, traceability, and human-in-the-loop review.

Mandatory disclaimer:

healthcare-monitor does not provide medical diagnosis or treatment decisions. It validates documentation structure and flags potential inconsistencies for human review.

---

## Product Boundary

healthcare-monitor is a reliability-focused clinical documentation MVP.

It is NOT:
- a diagnostic tool
- a treatment recommendation system
- an EHR replacement
- an autonomous medical decision system
- a generic “LLM converts text to JSON” demo

The product goal is to demonstrate:
- deterministic validation
- traceability
- auditability
- bounded retry/self-correction
- locally computed confidence
- human-in-the-loop review

---

## Target Pipeline

Planned pipeline:

Transcript Input
→ AI Structured Extraction
→ Schema Validation
→ Clinical Validation
→ Retry / Self-Correction
→ Confidence Scoring
→ Auto-save or Human Review
→ Trace + Evaluation Dashboard

Current implemented foundation supports this pipeline up to schema definition.

---

## Explicit MVP Scope

In scope:
- nursing/care transcript input
- AI-assisted structured extraction
- schema validation
- deterministic clinical validation for vitals/completeness
- one bounded retry/self-correction attempt
- system-derived confidence score
- auto-save vs human review routing
- full trace preservation
- review queue
- evaluation dashboard

Out of scope:
- voice/audio input
- authentication
- RBAC
- multi-tenancy
- RAG/vector database
- notifications
- realtime WebSocket
- real EHR integration
- diagnosis
- treatment decisions
- billing
- production deployment hardening beyond MVP

---

## Tech Stack

Backend:
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- Alembic
- Postgres target
- SQLite used for lightweight local migration verification
- OpenAI SDK
- httpx for Ollama
- uv
- pytest

Frontend planned:
- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod

Infra planned:
- Docker Compose

---

## Repository Structure

Expected/root-level structure:

healthcare-monitor/
- README.md
- CLAUDE.md
- TASKS.md
- ARCHITECTURE.md
- DECISIONS.md
- PROJECT_STATUS.md
- docker-compose.yml
- .env.example
- docs/
  - PRD.md
  - AI_PIPELINE.md
  - API.md
  - DESIGN_SYSTEM.md
  - TESTING.md
  - DEPLOYMENT.md
- prompts/
  - backend.md
  - frontend.md
  - review.md
  - debug.md
  - refactor.md
- examples/
  - good-transcript.txt
  - high-bp.txt
  - invalid-vitals.txt
  - missing-medication-dose.txt
  - german-note.txt
- backend/
  - app/
  - tests/
  - alembic/

Note:
Some earlier reports referenced both `healthcare-monitor/backend/` and `backend/`.
The current implementation appears to use `healthcare-monitor/backend/` as the backend root.
Docs should remain synchronized with this path.

---

## Phase Completion Status

### Phase 0 — Documentation Setup

Status: Complete

Completed:
- README completed
- docs/API.md completed
- docs/DEPLOYMENT.md completed
- docs and prompts prepared
- examples prepared
- TASKS.md Phase 0 marked complete

Purpose:
Establish documentation-first foundation and reduce implementation drift.

---

### Phase 1 — Backend Foundation

Status: Complete and verified

Implemented:
- FastAPI backend skeleton
- app entrypoint
- config/settings
- lazy database engine setup
- router structure
- health endpoint

Health endpoint:

GET /api/health

Expected minimal response:

{
  "status": "ok",
  "service": "healthcare-monitor-backend"
}

Important characteristics:
- Modules import without requiring live DB
- Engine is lazy
- No business logic implemented
- No AI orchestration implemented
- No validators implemented
- No frontend implemented

Files/areas involved:
- app/main.py
- app/core/config.py
- app/db/base.py
- app/db/session.py
- app/api/router.py
- app/api/routes/health.py
- app/models/
- app/services/
- pyproject.toml
- .env.example
- tests/test_health.py

Verification:
- uv sync succeeded
- pytest succeeded

---

### Phase 2 — Persistence Models + Migrations

Status: Complete and verified

Implemented SQLAlchemy 2.0 models:
- Run
- ValidationLog
- ReviewItem
- EvaluationResult

Implemented enums:
- Provider
- RunStatus
- IssueType
- ReviewStatus
- enum_column helper

Database structure:
- ValidationLog.run_id → runs.id
- ReviewItem.run_id → runs.id
- ON DELETE CASCADE
- relationships back to Run
- indexes added where needed

Alembic:
- alembic.ini
- alembic/env.py
- alembic/script.py.mako
- initial migration:
  - 0001_initial_initial_schema.py

Verification:
- uv sync succeeded
- alembic upgrade head succeeded on SQLite
- migration clean

Phase 2 assumptions:
- Enum storage uses portable VARCHAR + CHECK instead of native Postgres enums
- sa.Uuid and sa.JSON are used
- cost/confidence stored as Float
- some metrics nullable to allow persisting failed runs
- timestamps use Python-side defaults
- cascade delete chosen for traceability-safe cleanup

Important follow-up:
There is a known mismatch around validation issue shapes:
- ORM IssueType has: schema, clinical, warning, critical
- docs/API.md has field/severity/code shape
- Phase 4 schema has schema/clinical/completeness/format + severity

This must be reconciled before or during Phase 5.

---

### Phase 3 — AI Orchestration / Provider Abstraction

Status: Complete and verified

Implemented:
- Provider abstraction only
- No pipeline
- No routes
- No validation
- No persistence

Key files:
- app/services/prompts.py
- app/services/providers/__init__.py
- app/services/providers/base.py
- app/services/providers/pricing.py
- app/services/providers/openai_provider.py
- app/services/providers/ollama_provider.py
- app/services/providers/factory.py
- prompts/clinical_extraction_v1.md
- tests/test_providers.py

Modified:
- app/core/config.py
- .env.example
- pyproject.toml
- TASKS.md

Provider abstraction:
- ExtractionProvider ABC
- Template-method design
- Base provider owns:
  - prompt loading
  - latency timing
  - cost estimation
  - error normalization
- Subclasses implement low-level completion only

Shared result:
- ExtractionResult frozen dataclass
- fields:
  - provider
  - model
  - prompt_version
  - raw_response_text
  - content
  - latency_ms
  - estimated_cost
  - retryable_error
  - error
  - token counts
  - succeeded property

Provider implementations:
- OpenAIProvider
  - default model: gpt-4o-mini
  - JSON mode
  - temperature=0
  - lazy SDK import
- OllamaProvider
  - default model: qwen2.5
  - local /api/chat
  - format=json
  - lazy HTTP/runtime dependency

Prompt registry:
- file-based prompt registry
- prompt version:
  - clinical-extraction-v1
- prompt file:
  - prompts/clinical_extraction_v1.md

Factory:
- get_provider("openai" | "ollama", ...)
- accepts string or enum-like values

Config added:
- OPENAI_API_KEY
- OPENAI_MODEL
- OLLAMA_BASE_URL
- OLLAMA_MODEL

Cost:
- static per-token table
- local models cost = 0.0
- unknown models cost = 0.0

Verification:
- uv sync clean
- import checks succeeded
- OpenAIProvider and OllamaProvider factory smoke checks succeeded
- 8/8 tests passed
- no live OpenAI/Ollama call required

Important Phase 3 assumptions:
- Provider names remain strings matching Provider enum values
- Orchestration does not import ORM
- content = fence-stripped raw text, not schema-parsed
- JSON parsing belongs to Phase 4/5
- sync calls used for simplicity
- retryable errors include timeouts, connection errors, 5xx, rate limits
- missing key and most 4xx errors treated as permanent
- OpenAI SDK and httpx chosen over LiteLLM for inspectability

Reliability alignment:
- raw model output preserved
- provider/model/prompt version preserved
- latency/cost/token counts preserved
- errors normalized safely
- no provider-specific response leaks into later pipeline

---

### Phase 4 — Extraction Schemas

Status: Complete and verified

Implemented:
A schema-only Pydantic v2 layer.

No logic, no rules, no routes, no provider calls.

New files:
- app/schemas/common.py
- app/schemas/clinical_note.py
- app/schemas/validation.py
- app/schemas/process.py
- tests/test_schemas.py

Modified:
- app/schemas/__init__.py
- TASKS.md

pyproject.toml:
- untouched
- no new runtime dependencies required

Clinical entities implemented:
- PatientInfo
- BloodPressure
- HeartRate
- Temperature
- Spo2
- Vitals
- Medication
- Symptom
- Observation
- Action
- FollowUpNote
- ClinicalNote

ClinicalNote includes:
- patient
- vitals
- medications
- symptoms
- observations
- actions
- follow_up
- source_language
- note_summary
- extracted_at

Validation structure:
- ValidationIssue
  - severity
  - issue_type
  - field_path
  - message
  - rule_id

DTOs:
- ProcessRequest
  - transcript
  - provider
  - optional model override
- ProcessResponse
  - aligned with docs/API.md envelope over canonical payload types

Shared aliases:
- implemented in common.py
- exported via __init__.py

Verification:
- required schema import + JSON roundtrip script succeeded
- systolic int 138 preserved as int, not coerced to 