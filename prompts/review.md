# review.md

Use this prompt when reviewing or improving generated code.

## Review priorities
1. Scope correctness
2. Contract correctness
3. Validation safety
4. Traceability
5. Simplicity
6. Naming consistency
7. UI clarity

## Check for
- drift from MVP scope
- broken API contracts
- unsafe wording
- missing trace fields
- hidden coupling
- unnecessary abstractions
- over-engineering
- missing loading/empty/error states

## Output format
- Findings
- Risks
- Exact fixes
- Files to modify
- Do not rewrite unrelated areas
