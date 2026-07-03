# DECISIONS.md

## Decision 001 — MVP over platform
We are building a focused reliability prototype, not a full healthcare platform.

Reason:
A narrow, believable MVP is more valuable than a broad but shallow product.

## Decision 002 — Deterministic validation is mandatory
All schema and clinical validation must be local and deterministic.

Reason:
LLM-based validation is harder to trust and explain in a healthcare-sensitive workflow.

## Decision 003 — Confidence is derived, not self-reported
The system must never rely on model self-reported confidence.

Reason:
Self-reported confidence from LLMs is unreliable and not auditable.

## Decision 004 — Single retry only
The system allows one retry for self-correction.

Reason:
This keeps the behavior predictable, bounded, and easy to explain.

## Decision 005 — Human review is a first-class feature
Uncertain or invalid outputs are routed to a review queue.

Reason:
The point of the MVP is safe AI-assisted documentation, not autonomous automation.

## Decision 006 — Full trace persistence
Every run stores input, raw output, parsed output, validation results, retries, confidence, and decision.

Reason:
Without traceability, the system behaves like a black box.

## Decision 007 — Provider abstraction is required
The backend must support a provider interface for at least OpenAI and Ollama.

Reason:
This demonstrates engineering maturity and avoids hard-coupling to one API.

## Decision 008 — Synthetic data only
All examples and evaluations use synthetic transcripts.

Reason:
Avoid handling real patient data in an MVP portfolio project.

## Decision 009 — No auth in MVP
Authentication, RBAC, and roles are explicitly excluded.

Reason:
They add engineering overhead without improving the core reliability narrative.

## Decision 010 — Clinical Clarity UI
The UI must feel calm, clinical, reliable, and accessible.

Reason:
A healthcare-facing reliability tool should emphasize trust and precision, not novelty aesthetics.

## Decision 011 — Postgres for trace storage
Use Postgres as the primary datastore.

Reason:
It is simple, production-familiar, and sufficient for runs, logs, and review state.

## Decision 012 — FastAPI + Next.js
Use FastAPI for backend and Next.js for frontend.

Reason:
They provide rapid MVP development while keeping architecture credible and modern.
