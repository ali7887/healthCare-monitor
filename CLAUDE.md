
## `CLAUDE.md`

این فایل باید **مهم‌ترین فایل برای کنترل Claude Code** باشد.

```md
# CLAUDE.md

## Project identity
Project name: CareTrace

CareTrace is a healthcare AI reliability prototype focused on structured clinical documentation, deterministic validation, traceability, and human review.

## Primary goal
Build a lean but production-like MVP that demonstrates reliable handling of AI-generated clinical documentation outputs.

## Non-goals
Do not add:
- authentication
- RBAC
- multi-tenancy
- voice/audio streaming
- RAG
- vector databases
- realtime WebSockets
- notifications
- billing
- scheduling
- doctor/patient management
- real EHR integration
- diagnosis or treatment recommendations

## Product principles
1. Reliability over novelty
2. Deterministic validation over AI self-trust
3. Traceability over black-box behavior
4. Human review over unsafe automation
5. MVP discipline over feature sprawl


## Technical principles
1. Keep architecture simple and explicit
2. Use stable contracts between backend and frontend
3. Prefer typed schemas and deterministic logic
4. Store traces for every processing run
5. Keep prompts versioned and auditable
6. Avoid hidden magic and unnecessary abstractions

## UX principles
- calm, clinical, trustworthy
- no flashy AI visuals
- emphasize validation state and review state
- clearly distinguish extracted data from validated data
- use semantic status colors

## Working rules
When asked to make changes:
- only modify files required for the requested task
- do not refactor unrelated areas
- do not introduce new dependencies unless justified
- do not broaden scope beyond MVP
- preserve naming consistency across backend, frontend, and docs
- keep language precise and healthcare-safe

## Delivery rules
For each implementation step:
1. restate the scope briefly
2. list files to create or modify
3. implement only that scope
4. summarize what was done
5. list follow-up tasks, but do not implement them unless asked

## Backend constraints
- FastAPI
- Pydantic v2
- SQLAlchemy or SQLModel
- Postgres
- LiteLLM or equivalent provider abstraction
- deterministic validation logic must remain local

## Frontend constraints
- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod

## Data safety wording
Never present the system as diagnosing, prescribing, or recommending treatment.

Preferred wording:
- “structured documentation extraction”
- “validation issue”
- “flagged for human review”
- “potential inconsistency”

Avoid wording like:
- “diagnosis detected”
- “treatment recommended”
- “AI is certain”

## Processing flow
1. accept transcript
2. extract structured note
3. validate schema
4. validate clinical rules
5. retry once if validation failed
6. compute derived confidence
7. auto-save or route to review
8. store complete trace

## Important statuses
- auto_saved
- needs_review
- reviewed
- rejected
- failed

## Prompting policy
- keep prompts concise
- require structured JSON output
- capture prompt version
- include retry feedback only when needed
- never ask the model for confidence

## Testing priority
Highest priority tests:
1. schema validation
2. clinical validation rules
3. retry behavior
4. confidence scoring
5. routing decisions

## Documentation priority
When uncertain, align implementation to:
1. `README.md`
2. `ARCHITECTURE.md`
3. `docs/PRD.md`
4. `docs/API.md`
5. `DECISIONS.md`

## Execution Protocol (must always follow)

### Before coding:
1. Restate the exact scope in your own words.
2. List only the files you will modify.
3. Confirm what is explicitly out of scope.
4. Wait for user confirmation if scope is ambiguous.

### After coding:
1. What exact scope did you implement?
2. Which files changed?
3. What assumptions did you make?
4. What remains out of scope?
5. How does this align with CareTrace reliability goals?
