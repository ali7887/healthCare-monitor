# backend.md

Use this prompt when implementing backend tasks.

## Instruction
Implement only the requested backend scope for healthCare-monitor.

## Constraints
- FastAPI
- Pydantic v2
- SQLAlchemy or SQLModel
- Postgres
- deterministic validation only
- no auth
- no RBAC
- no RAG
- no websocket
- no diagnosis or treatment logic

## Rules
- modify only files required for this task
- keep code simple and explicit
- preserve API contracts from `docs/API.md`
- preserve architecture from `ARCHITECTURE.md`
- preserve product scope from `docs/PRD.md`
- do not invent extra features
- capture traceability fields where relevant

## Output format
1. Brief scope summary
2. Files created/modified
3. Implementation
4. Short summary
5. Any follow-up tasks not yet implemented