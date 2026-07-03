# API.md

## Base path
`/api`

## Conventions
- JSON request and response bodies
- ISO 8601 timestamps (UTC)
- Errors use standard HTTP status codes with a JSON body: `{ "detail": "message" }`
- No authentication in the MVP

## Shared types

### Status
One of:
- `auto_saved`
- `needs_review`
- `reviewed`
- `rejected`
- `failed`

### Provider
One of:
- `openai`
- `ollama`

### Severity
One of:
- `critical`
- `warning`
- `info`

### ValidationIssue
```json
{
  "field": "vitals.systolic_bp",
  "severity": "critical",
  "code": "out_of_range",
  "message": "Systolic BP value 320 mmHg is outside valid range 70–220."
}
```

### ClinicalNote (extracted output)
```json
{
  "patient_reference": "Anna Keller",
  "summary": "Reported mild dizziness in the morning.",
  "vitals": {
    "systolic_bp": 138,
    "diastolic_bp": 86,
    "heart_rate": 78,
    "temperature_c": 36.8,
    "spo2": 97
  },
  "medications": [
    { "name": "Metformin", "dose": "500mg", "route": "oral" }
  ]
}
```
Missing or unknown values are represented as `null` or omitted; the model must not infer unsupported values.

## Health

### GET `/api/health`
Returns service health status.

Response `200`:
```json
{ "status": "ok" }
```

## Processing

### POST `/api/process`
Process a transcript into a structured, validated clinical note.

Request:
```json
{
  "transcript": "Patient Anna Keller reported mild dizziness...",
  "provider": "openai"
}
```

Response `200`:
```json
{
  "run_id": "run_01H...",
  "status": "auto_saved",
  "provider": "openai",
  "prompt_version": "clinical-extraction-v1",
  "note": { "...": "ClinicalNote" },
  "issues": [ { "...": "ValidationIssue" } ],
  "retry_used": false,
  "confidence": 0.94,
  "latency_ms": 1820,
  "estimated_cost_usd": 0.0004,
  "created_at": "2026-07-03T09:00:00Z"
}
```

Notes:
- `status` and `confidence` are computed deterministically by the backend.
- Confidence is never taken from the model.
- A full trace is persisted regardless of outcome.

## Runs

### GET `/api/runs`
List processing runs, newest first.

Query parameters (optional):
- `status` — filter by `Status`
- `provider` — filter by `Provider`
- `limit` — default 50
- `offset` — default 0

Response `200`:
```json
{
  "items": [
    {
      "run_id": "run_01H...",
      "status": "needs_review",
      "provider": "openai",
      "confidence": 0.71,
      "retry_used": true,
      "created_at": "2026-07-03T09:00:00Z"
    }
  ],
  "total": 1
}
```

### GET `/api/runs/{run_id}`
Retrieve a single run summary and its structured output.

Response `200`:
```json
{
  "run_id": "run_01H...",
  "status": "needs_review",
  "provider": "openai",
  "prompt_version": "clinical-extraction-v1",
  "note": { "...": "ClinicalNote" },
  "issues": [ { "...": "ValidationIssue" } ],
  "retry_used": true,
  "confidence": 0.71,
  "created_at": "2026-07-03T09:00:00Z"
}
```

Errors:
- `404` if the run does not exist.

## Trace

### GET `/api/runs/{run_id}/trace`
Retrieve the full run trace for auditability.

Response `200`:
```json
{
  "run_id": "run_01H...",
  "transcript": "Patient Anna Keller reported mild dizziness...",
  "provider": "openai",
  "prompt_version": "clinical-extraction-v1",
  "raw_output": "{...raw model text...}",
  "parsed_output": { "...": "ClinicalNote" },
  "issues": [ { "...": "ValidationIssue" } ],
  "retry_used": true,
  "retry_reason": "schema_validation_failed",
  "confidence": 0.71,
  "status": "needs_review",
  "latency_ms": 2450,
  "estimated_cost_usd": 0.0006,
  "created_at": "2026-07-03T09:00:00Z"
}
```

Errors:
- `404` if the run does not exist.

## Review queue

### GET `/api/review`
List runs routed for human review.

Response `200`:
```json
{
  "items": [
    {
      "run_id": "run_01H...",
      "status": "needs_review",
      "confidence": 0.71,
      "critical_issue_count": 1,
      "created_at": "2026-07-03T09:00:00Z"
    }
  ],
  "total": 1
}
```

### POST `/api/review/{run_id}/approve`
Approve a flagged run as-is.

Response `200`:
```json
{ "run_id": "run_01H...", "status": "reviewed" }
```

### POST `/api/review/{run_id}/edit`
Approve a flagged run with human-corrected structured output.

Request:
```json
{ "note": { "...": "ClinicalNote" } }
```

Response `200`:
```json
{ "run_id": "run_01H...", "status": "reviewed" }
```

### POST `/api/review/{run_id}/reject`
Reject a flagged run.

Request (optional):
```json
{ "reason": "Values not clinically plausible." }
```

Response `200`:
```json
{ "run_id": "run_01H...", "status": "rejected" }
```

Errors for review actions:
- `404` if the run does not exist.
- `409` if the run is not in a reviewable state.

## Evaluation

### GET `/api/evaluation`
Aggregated reliability metrics for the evaluation dashboard.

Response `200`:
```json
{
  "totals": {
    "runs": 42,
    "auto_saved": 30,
    "needs_review": 9,
    "reviewed": 6,
    "rejected": 3,
    "failed": 0
  },
  "by_provider": [
    {
      "provider": "openai",
      "runs": 24,
      "auto_save_rate": 0.75,
      "retry_rate": 0.21,
      "avg_confidence": 0.88,
      "avg_latency_ms": 1900,
      "estimated_cost_usd": 0.012
    }
  ]
}
```

## Notes on stability
- Field names must remain stable across backend, frontend, and docs.
- Any contract change must be reflected here first, then in code.
