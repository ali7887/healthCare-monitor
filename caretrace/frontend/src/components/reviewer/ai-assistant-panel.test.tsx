import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithClient } from "@/test/utils";
import type { AssistantAnalysis, RunDetail } from "@/lib/api/types";

// Mock only the network edge; the hook, its states, and the component render for
// real through React Query.
const analyzeReview = vi.fn();
vi.mock("@/lib/api/assistant", () => ({
  analyzeReview: (...args: unknown[]) => analyzeReview(...args),
}));

import { AiAssistantPanel } from "@/components/reviewer/ai-assistant-panel";

function makeRun(over: Partial<RunDetail> = {}): RunDetail {
  return {
    id: "run-1",
    provider: "openai",
    status: "needs_review",
    transcript: "t",
    parsed_output: { medications: [{ name: "Amlodipine", dose: "10mg" }] },
    final_output: null,
    confidence_score: 0.7,
    confidence_breakdown: null,
    routing_decision: "human_review",
    routing_reason: "low confidence",
    retry_count: 0,
    warnings_count: 0,
    latency_ms: 10,
    cost: 0.0002,
    raw_model_response: "{}",
    issues: [],
    created_at: "2026-07-01T00:00:00Z",
    pending_review_id: "rev-1",
    reasoning_summary: null,
    reviewer_notes: null,
    ...over,
  };
}

const RISK_RESULT: AssistantAnalysis = {
  clinical_risks: ["Dose for 'Amlodipine' changed from '10mg' to '5mg' — verify against the medication chart."],
  suggestion: "Review the flagged concern(s) before approving.",
  confidence_score: 0.72,
};

const STABLE_RESULT: AssistantAnalysis = {
  clinical_risks: [],
  suggestion: "No additional clinical concerns were detected in the current output.",
  confidence_score: 0.95,
};

beforeEach(() => {
  analyzeReview.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("AiAssistantPanel", () => {
  it("is hidden when the run is already reviewed", () => {
    const { container } = renderWithClient(
      <AiAssistantPanel run={makeRun({ status: "reviewed" })} />
    );
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId("ai-assistant-panel")).not.toBeInTheDocument();
  });

  it("is hidden when the run is already rejected", () => {
    const { container } = renderWithClient(
      <AiAssistantPanel run={makeRun({ status: "rejected" })} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("requests analysis on click and surfaces a risk alert", async () => {
    analyzeReview.mockResolvedValue(RISK_RESULT);
    renderWithClient(<AiAssistantPanel run={makeRun()} />);

    // No result before the user asks.
    expect(screen.queryByTestId("assistant-result")).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId("assistant-analyze-button"));

    await waitFor(() =>
      expect(analyzeReview).toHaveBeenCalledWith("run-1", {
        medications: [{ name: "Amlodipine", dose: "10mg" }],
      })
    );

    expect(await screen.findByTestId("assistant-risks")).toHaveTextContent(/Amlodipine/);
    expect(screen.getByText("Risk alert")).toBeInTheDocument();
    // The assistant's numeric confidence is intentionally not displayed:
    // only the pipeline's derived confidence is presented as a scored signal.
    expect(screen.queryByText(/assistant confidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText("72%")).not.toBeInTheDocument();
  });

  it("shows a stable state when no risks are found", async () => {
    analyzeReview.mockResolvedValue(STABLE_RESULT);
    renderWithClient(<AiAssistantPanel run={makeRun()} />);

    await userEvent.click(screen.getByTestId("assistant-analyze-button"));

    expect(await screen.findByTestId("assistant-stable")).toBeInTheDocument();
    expect(screen.getByText("Stable")).toBeInTheDocument();
    expect(screen.queryByTestId("assistant-risks")).not.toBeInTheDocument();
  });

  it("surfaces an error alert when analysis fails", async () => {
    analyzeReview.mockRejectedValue(new Error("Run not found"));
    renderWithClient(<AiAssistantPanel run={makeRun()} />);

    await userEvent.click(screen.getByTestId("assistant-analyze-button"));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not run analysis/i);
    expect(alert).toHaveTextContent(/run not found/i);
  });
});
