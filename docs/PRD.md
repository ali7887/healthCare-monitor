# PRD.md

## Product name
CareTrace

## Subtitle
Reliable AI-assisted clinical documentation with validation, traceability, and human review.

## Problem
Nursing and caregiver notes are often entered as free text. Free text is difficult to structure, validate, search, and audit. Naive LLM extraction may produce malformed, incomplete, or clinically implausible outputs. Sensitive healthcare workflows require controlled automation and human oversight.

## Target outcome
Convert unstructured transcript text into structured clinical notes while:
- validating output shape
- flagging inconsistent values
- retrying once for self-correction
- deriving confidence locally
- routing uncertain results to human review
- preserving full traces

## Primary users
- healthcare AI evaluators
- product engineering reviewers
- internal clinical operations demo users
- human reviewer role in the prototype

## Core user stories
1. As a user, I can paste a transcript and process it into structured output.
2. As a user, I can choose which provider to use.
3. As a user, I can see validation issues clearly.
4. As a reviewer, I can inspect flagged runs and approve, edit, or reject them.
5. As an evaluator, I can compare models by reliability and cost-related metrics.

## MVP features
- transcript input
- example transcript loader
- provider switcher
- structured extraction
- schema validation
- clinical rule validation
- single retry loop
- confidence scoring
- auto-save or review routing
- review queue
- trace storage
- runs history
- evaluation dashboard

## Non-features
- authentication
- RBAC
- RAG
- vector DB
- voice input
- notifications
- real EHR integration
- diagnosis/treatment logic
- multi-tenant SaaS features

## Success criteria
- valid transcript can be processed end-to-end
- invalid or inconsistent transcript is flagged deterministically
- review queue is populated correctly
- trace data is visible and complete
- provider comparison is demonstrable
- UI communicates safety and review state clearly

## Risks
- over-engineering
- mixing extraction with diagnosis language
- relying on AI for validation
- poorly defined API contracts
- frontend/backend drift

## Mitigations
- docs-first approach
- strict schema contracts
- deterministic validators
- narrow scope
- prompt versioning
- explicit status model
