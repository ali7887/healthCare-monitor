import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuditTrail } from "@/components/runs/audit-trail";
import type { RunDetail } from "@/lib/api/types";

function makeRun(over: Partial<RunDetail> = {}): RunDetail {
  return {
    id: "run-1",
    provider: "openai",
    status: "auto_saved",
    transcript: "t",
    parsed_output: { a: 1 },
    final_output: { a: 1 },
    confidence_score: 0.95,
    confidence_breakdown: null,
    routing_decision: "auto_save",
    routing_reason: "No validation issues; saved automatically.",
    retry_count: 0,
    warnings_count: 0,
    latency_ms: 800,
    cost: 0.0002,
    raw_model_response: "{}",
    issues: [],
    created_at: "2026-07-06T10:14:02Z",
    pending_review_id: null,
    reasoning_summary: null,
    reviewer_notes: null,
    reviewed_at: null,
    ...over,
  };
}

describe("AuditTrail", () => {
  it("shows the AI parse step with the provider brand name", () => {
    render(<AuditTrail run={makeRun()} />);
    expect(screen.getByText(/parsed by ai \(openai\)/i)).toBeInTheDocument();
    expect(screen.getByText(/routed: auto-save/i)).toBeInTheDocument();
  });

  it("lists each validation issue as a flagged event", () => {
    const run = makeRun({
      status: "needs_review",
      routing_decision: "human_review",
      issues: [
        {
          severity: "warning",
          issue_type: "clinical",
          field_path: "vitals.heart_rate.value",
          message: "Heart rate above expected range.",
          rule_id: "WARN_HR_HIGH",
        },
      ],
    });
    render(<AuditTrail run={run} />);
    expect(screen.getByText(/flagged: heart rate above expected range/i)).toBeInTheDocument();
  });

  it("adds a human decision step with a timestamp for decided runs", () => {
    const run = makeRun({
      status: "reviewed",
      routing_decision: "human_review",
      reviewer_notes: "Verified against chart.",
      reviewed_at: "2026-07-06T10:15:32Z",
      final_output: { a: 2 },
      parsed_output: { a: 1 },
    });
    render(<AuditTrail run={run} />);
    // Output changed before approval → "Modified and approved".
    expect(screen.getByText(/modified and approved by reviewer/i)).toBeInTheDocument();
    expect(screen.getByText(/status updated to reviewed/i)).toBeInTheDocument();
    // The human decision carries its own recorded timestamp (10:15 UTC), not
    // the run's creation time (10:14).
    expect(screen.getAllByText(/10:15 UTC/).length).toBeGreaterThan(0);
  });

  it("marks a failed extraction distinctly", () => {
    const run = makeRun({
      status: "failed",
      routing_decision: null,
      parsed_output: null,
      final_output: null,
      confidence_score: null,
    });
    render(<AuditTrail run={run} />);
    expect(screen.getByText(/extraction by openai failed/i)).toBeInTheDocument();
  });
});
