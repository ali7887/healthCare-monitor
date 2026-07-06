"use client";

import { ListChecks, Sparkles } from "lucide-react";

import { StatusBadge, type Tone } from "@/components/common/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatConfidence } from "@/lib/format";
import type { RunDetail, Severity, ValidationIssue } from "@/lib/api/types";

// Confidence thresholds mirror the backend routing engine.
const AUTO_SAVE = 0.85;
const REVIEW_LOW = 0.7;

function confidenceMeta(score: number): { tone: Tone; color: string; label: string } {
  if (score >= AUTO_SAVE) {
    return { tone: "success", color: "#10b981", label: "High — clears auto-save" };
  }
  if (score >= REVIEW_LOW) {
    return { tone: "warning", color: "#f59e0b", label: "Moderate — review band" };
  }
  return { tone: "danger", color: "#f43f5e", label: "Low — flagged" };
}

function ConfidenceMeter({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <div data-testid="confidence-meter" className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-foreground">Derived confidence</span>
          <span className="tabular-nums text-muted-foreground">n/a</span>
        </div>
        <p className="text-xs text-muted-foreground">
          No confidence was derived — extraction did not produce a valid note.
        </p>
      </div>
    );
  }
  const pct = Math.round(score * 100);
  const meta = confidenceMeta(score);
  return (
    <div data-testid="confidence-meter" className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">Derived confidence</span>
        <span className="tabular-nums font-semibold" style={{ color: meta.color }}>
          {formatConfidence(score)}
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Derived confidence"
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: meta.color }}
        />
      </div>
      <StatusBadge tone={meta.tone}>{meta.label}</StatusBadge>
    </div>
  );
}

const SEVERITY_META: Record<Severity, { tone: Tone; label: string }> = {
  critical: { tone: "danger", label: "High" },
  warning: { tone: "warning", label: "Medium" },
};

function PolicyViolations({ issues }: { issues: ValidationIssue[] }) {
  return (
    <div data-testid="policy-violations" className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">Clinical policy violations</h4>
      {issues.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          None — all deterministic checks passed.
        </p>
      ) : (
        <ul className="space-y-2">
          {issues.map((issue, i) => {
            const meta = SEVERITY_META[issue.severity] ?? SEVERITY_META.warning;
            return (
              <li
                key={i}
                className="flex items-start gap-2.5 rounded-md border bg-muted/30 p-2.5"
              >
                <StatusBadge tone={meta.tone}>{meta.label}</StatusBadge>
                <div className="min-w-0 space-y-0.5">
                  <p className="text-sm text-foreground">{issue.message}</p>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    {issue.rule_id ?? issue.issue_type}
                    {issue.field_path ? ` · ${issue.field_path}` : ""}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** Parse the newline-separated "Step N: ..." summary into ordered items. */
function parseSteps(summary: string): string[] {
  return summary
    .split("\n")
    .map((line) => line.replace(/^\s*Step\s*\d+\s*:\s*/i, "").trim())
    .filter(Boolean);
}

function ReasoningSteps({ summary }: { summary: string | null }) {
  const steps = summary ? parseSteps(summary) : [];
  return (
    <div data-testid="reasoning-summary" className="space-y-2">
      <h4 className="text-sm font-semibold text-foreground">Decision path</h4>
      {steps.length === 0 ? (
        <p className="text-sm text-muted-foreground">No reasoning summary recorded.</p>
      ) : (
        <ol className="space-y-1.5">
          {steps.map((step, i) => (
            <li key={i} className="flex gap-2.5 text-sm text-foreground">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">
                {i + 1}
              </span>
              <span className="leading-relaxed">{step}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/**
 * Reasoning Explanation panel (Phase 20): visually demystifies *why* a run was
 * routed the way it was — the derived-confidence meter ("derived" because the
 * score is computed deterministically from penalties, never self-reported by
 * the model), the clinical policy
 * violations that fired, and the step-by-step decision path. For a decided run
 * it also shows the operator's notes as a read-only audit trail (the editable
 * notes field for a pending run lives in the review workspace).
 */
export function ReasoningPanel({ run }: { run: RunDetail }) {
  const decided = run.status === "reviewed" || run.status === "rejected";
  return (
    <Card data-testid="reasoning-panel">
      <CardHeader className="flex flex-row items-center gap-2 space-y-0">
        <Sparkles className="h-4 w-4 text-primary" />
        <CardTitle className="text-base">Reasoning explanation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <ConfidenceMeter score={run.confidence_score} />
        <PolicyViolations issues={run.issues} />
        <ReasoningSteps summary={run.reasoning_summary} />

        {decided && run.reviewer_notes ? (
          <div data-testid="reviewer-notes-audit" className="space-y-2">
            <h4 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
              <ListChecks className="h-3.5 w-3.5 text-muted-foreground" />
              Reviewer notes
            </h4>
            <p className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm text-foreground">
              {run.reviewer_notes}
            </p>
            <p className="text-[11px] text-muted-foreground">
              Recorded by the operator at decision time (read-only).
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
