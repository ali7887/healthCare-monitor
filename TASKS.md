# TASKS.md

## Phase 0 — Documentation
- [x] Write README.md
- [x] Write CLAUDE.md
- [x] Write ARCHITECTURE.md
- [x] Write DECISIONS.md
- [x] Write docs/PRD.md
- [x] Write docs/AI_PIPELINE.md
- [x] Write docs/API.md
- [x] Write docs/DESIGN_SYSTEM.md
- [x] Write docs/TESTING.md
- [x] Write docs/DEPLOYMENT.md
- [x] Write prompts/*.md
- [x] Write examples/*.txt

## Phase 1 — Backend foundation
- [x] Initialize FastAPI app
- [x] Add config and settings
- [x] Add DB session and base metadata
- [x] Add `/api/health`
- [x] Add backend `.env.example`

## Phase 2 — Persistence models
- [x] Create Run model
- [x] Create ValidationLog model
- [x] Create ReviewItem model
- [x] Create EvaluationResult model
- [x] Define enums and statuses
- [x] Add migrations strategy

## Phase 3 — AI orchestration
- [x] Define provider interface
- [x] Implement OpenAI provider
- [x] Implement Ollama provider
- [x] Add prompt versioning
- [x] Capture raw response
- [x] Normalize provider output shape

## Phase 4 — Extraction schemas
- [x] Define ClinicalNote schema
- [x] Define Vitals schema
- [x] Define Medication schema
- [x] Define validation issue schema
- [x] Define process request/response schemas

## Phase 5 — Validation engine
- [ ] Add schema validation handling
- [ ] Add BP range rules
- [ ] Add HR range rules
- [ ] Add temperature rules
- [ ] Add SpO2 rules
- [ ] Add medication dose requirement
- [ ] Add unit validation
- [ ] Add extra-field detection
- [ ] Add issue formatter

## Phase 6 — Retry logic
- [ ] Retry once on validation failure
- [ ] Build retry feedback prompt
- [ ] Re-validate second output
- [ ] Trace retry count and retry reasons

## Phase 7 — Confidence and routing
- [ ] Implement derived confidence function
- [ ] Implement routing decision logic
- [ ] Define auto-save threshold
- [ ] Define review override rules

## Phase 8 — Processing and trace APIs
- [ ] Implement process endpoint
- [ ] Implement runs list endpoint
- [ ] Implement run detail endpoint
- [ ] Implement trace detail endpoint
- [ ] Implement review queue endpoints
- [ ] Persist latency and cost estimates

## Phase 9 — Frontend shell
- [ ] Initialize Next.js app
- [ ] Add global layout and sidebar
- [ ] Add theme tokens
- [ ] Add shared UI primitives
- [ ] Add API client
- [ ] Add query client

## Phase 10 — Process console
- [ ] Build transcript input panel
- [ ] Add example loader
- [ ] Add provider selector
- [ ] Add process action
- [ ] Add pipeline stepper
- [ ] Add structured output panel
- [ ] Add validation results panel
- [ ] Add confidence and decision card

## Phase 11 — Runs and review
- [ ] Build runs table
- [ ] Build review queue table
- [ ] Build review detail page
- [ ] Add approve action
- [ ] Add edit and approve action
- [ ] Add reject action

## Phase 12 — Evaluation dashboard
- [ ] Add metrics cards
- [ ] Add model comparison table
- [ ] Add simple evaluation summary
- [ ] Add provider performance view

## Phase 13 — Polish
- [ ] Add loading states
- [ ] Add empty states
- [ ] Add error states
- [ ] Improve responsiveness
- [ ] Add screenshots to README
- [ ] Add demo script
- [ ] Add short case study

## Done criteria
- [ ] MVP can process sample transcripts end-to-end
- [ ] Invalid outputs are flagged safely
- [ ] Review queue works
- [ ] Trace data is visible
- [ ] Evaluation dashboard is populated
- [ ] Docs and examples are complete
