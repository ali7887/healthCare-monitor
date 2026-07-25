import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { EvaluationSummary } from "@/lib/api/types";

const useEvaluation = vi.fn();
vi.mock("@/lib/hooks/use-evaluation", () => ({
  useEvaluation: () => useEvaluation(),
}));

import { EvaluationView } from "@/components/evaluation/evaluation-view";

afterEach(() => vi.clearAllMocks());

const SUMMARY: EvaluationSummary = {
  totals: {
    runs: 10,
    auto_saved: 6,
    needs_review: 2,
    reviewed: 1,
    rejected: 1,
    failed: 0,
  },
  by_provider: [
    {
      provider: "openai",
      runs: 8,
      auto_save_rate: 0.75,
      retry_rate: 0.25,
      avg_confidence: 0.88,
      avg_latency_ms: 900,
      estimated_cost_usd: 0.0016,
    },
    {
      provider: "ollama",
      runs: 2,
      auto_save_rate: 0.5,
      retry_rate: 0.0,
      avg_confidence: 0.7,
      avg_latency_ms: 1500,
      estimated_cost_usd: 0.0,
    },
  ],
};

describe("EvaluationView", () => {
  it("renders a provider comparison row per provider", () => {
    useEvaluation.mockReturnValue({ data: SUMMARY, isLoading: false, isError: false });
    render(<EvaluationView />);

    expect(screen.getByText("OpenAI")).toBeInTheDocument();
    expect(screen.getByText("Ollama")).toBeInTheDocument();
    // Auto-save rate rendered as a percentage.
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("offers JSON and CSV exports pointing at the export endpoint", () => {
    useEvaluation.mockReturnValue({ data: SUMMARY, isLoading: false, isError: false });
    render(<EvaluationView />);

    expect(screen.getByTestId("export-json")).toHaveAttribute(
      "href",
      expect.stringContaining("/evaluation/export?format=json")
    );
    expect(screen.getByTestId("export-csv")).toHaveAttribute(
      "href",
      expect.stringContaining("/evaluation/export?format=csv")
    );
  });

  it("surfaces the error state with a retry", () => {
    const refetch = vi.fn();
    useEvaluation.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch,
    });
    render(<EvaluationView />);
    expect(screen.getByText(/unable to load evaluation metrics/i)).toBeInTheDocument();
  });
});
