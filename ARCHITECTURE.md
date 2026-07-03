# ARCHITECTURE.md

## System goal
CareTrace transforms unstructured nursing or caregiver transcripts into structured clinical documentation while emphasizing validation, traceability, and human review.

## Architectural priorities
1. deterministic validation
2. provider abstraction
3. full run traceability
4. minimal but clear workflow separation
5. MVP simplicity

## High-level components

### Frontend
Next.js application with pages for:
- Dashboard
- Process
- Runs
- Review Queue
- Evaluation
- Trace Detail

### Backend
FastAPI service responsible for:
- transcript processing
- provider orchestration
- schema validation
- clinical validation
- confidence scoring
- routing decisions
- persistence
- metrics aggregation

### Storage
Postgres stores:
- processing runs
- validation issues
- review queue items
- evaluation results

## Processing pipeline
1. User submits transcript and provider choice
2. Backend selects provider client
3. LLM returns structured candidate output
4. Output is parsed and validated against schema
5. Clinical deterministic rules are evaluated
6. If validation fails, retry once with structured feedback
7. Final issues are collected
8. Confidence score is derived locally
9. Run is auto-saved or routed to human review
10. Full trace is persisted

## Backend modules

### API layer
Routes expose:
- health
- processing
- run history
- review queue
- evaluation

### AI orchestration layer
Responsibilities:
- provider abstraction
- prompt versioning
- raw response capture
- retry prompt generation
- normalized output contract

### Validation layer
Responsibilities:
- schema compliance
- field type checks
- clinical range validation
- medication completeness checks
- issue normalization with severity levels

### Tracing layer
Responsibilities:
- persist input transcript
- persist selected provider
- persist prompt version
- persist raw model output
- persist parsed output
- persist validation issues
- persist retry count
- persist confidence
- persist decision
- persist latency and cost estimate

## Core entities

### Run
Represents one transcript processing execution.

### ValidationLog
Represents one validation issue associated with a run.

### ReviewItem
Represents a run routed for human review.

### EvaluationResult
Stores aggregated or dataset-level evaluation outputs.

## Decision model
A run can end in:
- auto_saved
- needs_review
- reviewed
- rejected
- failed

## Confidence model
Confidence is derived from:
- retry usage
- critical issue count
- warning count
- missing required fields

Model-reported confidence is never trusted.

## Safety boundaries
The system:
- structures clinical documentation
- flags inconsistencies
- supports human review

The system does not:
- diagnose
- prescribe
- recommend treatment
- make autonomous medical decisions

## Deployment shape
For MVP:
- frontend and backend run separately
- Postgres via Docker Compose
- OpenAI key via environment
- optional Ollama local provider

## Future extensibility
Future extensions may include:
- richer multilingual support
- dataset-driven evaluation automation
- more advanced unit normalization
- batch processing
- audit exports

These are intentionally out of scope for the MVP implementation.
