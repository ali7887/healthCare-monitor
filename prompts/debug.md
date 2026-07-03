# debug.md

Use this prompt when debugging CareTrace.

## Debug method
1. Identify exact failing scope
2. Reproduce with minimal context
3. Check contract mismatch first
4. Check schema mismatch second
5. Check validation assumptions third
6. Propose smallest safe fix

## Rules
- do not refactor broadly during debugging
- do not change API contracts unless necessary
- keep fixes local
- preserve deterministic validation behavior
- preserve trace capture

## Output format
- Problem summary
- Likely root cause
- Minimal fix
- Files to modify
- Verification steps
