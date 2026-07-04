# TESTING.md

## Testing goals
Ensure healthCare-monitor is reliable, deterministic, and explainable in core workflows.

## Test categories

### Unit tests
Focus on:
- schema parsing
- clinical rules
- confidence calculation
- routing decisions
- issue formatting

### Integration tests
Focus on:
- process endpoint
- provider normalization
- retry loop behavior
- persistence of run traces
- review queue insertion

### UI tests
Focus on:
- process form submission
- validation results rendering
- review queue display
- approve/edit/reject actions
- evaluation dashboard rendering

## Highest-priority test cases

### Schema validation
- valid JSON passes
- invalid JSON fails
- wrong field type fails
- missing nested object fails
- unknown extra fields are flagged if policy requires it

### Clinical validation
- valid BP passes
- systolic below range is flagged
- systolic above range is flagged
- diastolic outside range is flagged
- heart rate outside range is flagged
- temperature outside range is flagged
- SpO2 below 90 gives warning
- SpO2 below 70 gives critical
- medication without dose gives warning
- unknown unit gives warning

### Retry loop
- retry occurs once on validation failure
- corrected second output passes
- second failure routes to review
- retry count is persisted

### Confidence
- retry reduces score
- critical issues reduce score
- warnings reduce score
- missing required field reduces score
- critical issue still forces review even if score is high

### Routing
- high confidence and no critical issues => auto-save
- low confidence => needs review
- schema failure after retry => needs review

## Synthetic data only
All tests and fixtures must use synthetic transcripts and synthetic structured outputs.

## Suggested backend test files
- `test_schema_validation.py`
- `test_clinical_rules.py`
- `test_confidence.py`
- `test_process_flow.py`

## Suggested frontend test scope
Keep frontend tests lightweight for MVP. Prioritize critical render and interaction flows only.
