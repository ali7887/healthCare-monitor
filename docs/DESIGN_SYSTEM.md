# DESIGN_SYSTEM.md

## Theme name
Clinical Clarity

## Design goals
- calm
- clinical
- reliable
- precise
- accessible
- not flashy

## Color palette

### Primary
- Primary: `#0F766E`
- Primary Hover: `#115E59`
- Primary Soft: `#CCFBF1`

### Neutrals
- Background: `#F8FAFC`
- Surface: `#FFFFFF`
- Surface Muted: `#F1F5F9`
- Text Primary: `#0F172A`
- Text Secondary: `#475569`
- Text Muted: `#64748B`
- Border: `#E2E8F0`
- Divider: `#CBD5E1`

### Semantic
- Success: `#15803D`
- Success Soft: `#DCFCE7`
- Warning: `#D97706`
- Warning Soft: `#FEF3C7`
- Danger: `#DC2626`
- Danger Soft: `#FEE2E2`
- Info: `#2563EB`
- Info Soft: `#DBEAFE`

## Typography
- UI font: Inter
- Mono font: JetBrains Mono

Recommended sizing:
- base text: 14–15px
- labels: 12–13px
- metrics: 24–32px
- line-height: 1.5–1.7

## Component guidance

### Cards
- white background
- subtle border
- radius 12px
- subtle shadow
- 20–24px padding

### Buttons
Primary:
- teal background
- white text
- rounded 10px

Secondary:
- white background
- neutral border
- slate text

Danger:
- red background
- white text

### Status badges
- auto-saved: green
- needs review: amber
- critical issue: red
- reviewed: blue/slate
- retry used: amber outline

### Alerts
Alerts must be explicit and actionable.

Good:
- “Critical validation failed”
- “Systolic BP value 400 mmHg is outside valid range 70–220.”
- “This run has been routed to human review.”

Bad:
- “Something went wrong”
- “AI is confident”
- “Diagnosis detected”

## Layout
Sidebar items:
- Dashboard
- Process
- Runs
- Review Queue
- Evaluation
- Trace

## UX behavior
Users should quickly understand:
- whether the note is safe to auto-save
- whether review is required
- which fields were extracted
- which fields were flagged
- why a decision was made

## Motion
Keep animation minimal and functional only.

## Accessibility
- strong contrast
- large hit targets
- semantic color plus text labels
- readable numeric presentation for vitals

## Content style
Preferred phrases:
- “needs human review”
- “validation issue”
- “structured extraction completed”
- “flagged for review”

Avoid:
- “AI decided”
- “medical recommendation”
- “diagnosis”