import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeTestQueryClient, renderWithClient } from "@/test/utils";
import type { DashboardStats } from "@/lib/api/types";

const getDashboardStats = vi.fn();
vi.mock("@/lib/api/dashboard", () => ({
  getDashboardStats: () => getDashboardStats(),
}));

import { KpiStrip } from "@/components/dashboard/kpi-strip";

const BEFORE: DashboardStats = {
  total_runs: 4,
  accepted_runs: 2,
  routed_to_human_runs: 1,
  rejected_runs: 1,
  average_confidence: 0.71,
};
const AFTER: DashboardStats = {
  total_runs: 9,
  accepted_runs: 5,
  routed_to_human_runs: 2,
  rejected_runs: 2,
  average_confidence: 0.8,
};

beforeEach(() => getDashboardStats.mockReset());
afterEach(() => vi.clearAllMocks());

describe("KpiStrip", () => {
  it("renders the aggregate metrics once loaded", async () => {
    getDashboardStats.mockResolvedValue(BEFORE);
    renderWithClient(<KpiStrip />);
    expect(await screen.findByText("4")).toBeInTheDocument();
  });

  it("reflects new counts after the dashboard cache is invalidated (post-mutation)", async () => {
    getDashboardStats.mockResolvedValueOnce(BEFORE).mockResolvedValueOnce(AFTER);
    const client = makeTestQueryClient();
    renderWithClient(<KpiStrip />, { client });

    expect(await screen.findByText("4")).toBeInTheDocument();

    // This is exactly what useRunAction.onSuccess does after a decision.
    await client.invalidateQueries({ queryKey: ["dashboard"] });

    await waitFor(() => expect(screen.getByText("9")).toBeInTheDocument());
    expect(screen.queryByText("4")).not.toBeInTheDocument();
  });
});
