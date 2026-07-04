# AI_PIPELINE.md

## Goal
Define the end-to-end AI processing pipeline for healthCare-monitor.

## Pipeline stages

### 1. Transcript intake
Input:
- transcript text
- selected provider
- optional demo/example context

Output:
- processing request payload

### 2. Structured extraction
The provider receives a prompt instructing it to produce a strict JSON representation of the transcript.

Requirements:
- no diagnosis
- no treatment recommendation
- no unsupported inference
- preserve uncertainty as null or omission
- output only target schema fields

### 3. Schema validation
The system parses provider output and validates it against the Pydantic schema.

Possible outcomes:
- pass
- fail due to invalid JSON
- fail due to missing fields
- fail due to wrong types
- fail due to invalid nested structure

### 4. Clinical validation
Deterministic local rules inspect extracted values.

Initial rule set:
- systolic BP: 70–220 mmHg
- diastolic BP: 40–130 mmHg
- heart rate: 40–180 bpm
- temperature: 35.0–42.0 °C
- SpO2: 70–100%
- SpO2 < 90: warning
- medication dose required if medication exists
- unknown units flagged

### 5. Retry loop
If schema validation or clinical validation fails in a way that may be correctable, one retry is allowed.

Retry input includes:
- structured error summary
- reminder of target schema
- instruction to correct output only

### 6. Final validation
The retried output is validated again.

### 7. Confidence calculation
Confidence starts at 1.0 and is reduced by deterministic penalties.

Suggested formula:
- -0.25 if retry was used
- -0.15 per critical issue
- -0.08 per warning
- -0.20 if required field is missing

### 8. Routing decision
Rules:
- critical issue => needs review
- schema failure after retry => needs review
- confidence < 0.85 => needs review
- otherwise => auto-save

### 9. Trace persistence
Persist:
- transcript
- provider
- prompt version
- raw model output
- parsed output
- validation issues
- retry count
- confidence
- final status
- latency
- estimated cost

## Safety constraints
- never ask the model for confidence
- never use the model to decide whether output is medically safe
- never generate diagnosis or treatment recommendations

## Prompt versioning
Store a stable prompt identifier such as:
`clinical-extraction-v1`

## Provider normalization
All providers must normalize to the same internal response shape before validation.

## Failure handling
If parsing fails completely after retry:
- mark run as failed or needs_review based on implementation choice
- persist raw output
- store validation issues
- do not silently discard evidence
