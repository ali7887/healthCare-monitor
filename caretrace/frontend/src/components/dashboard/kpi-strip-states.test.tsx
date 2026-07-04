import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

// These assert the KPI strip's presentational branches (error / loading) in
// isolation, so we stub the data hook directly rather than driving a rejected
// query through React Query.
const useDashboardStats = vi.fn();
vi.mock("@/lib/hooks/use-dashboard-stats", () => ({
  useDashboardStats: () => useDashboardStats(),
}));

import { KpiStrip } from "@/components/dashboard/kpi-strip";

afterEach(() => vi.clearAllMocks());

describe("KpiStrip states", () => {
  it("shows the error surface with a retry that refetches", async () => {
    const refetch = vi.fn();
    useDashboardStats.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch });

    render(<KpiStrip />);
    expect(screen.getByText(/unable to load dashboard metrics/i)).toBeInTheDocument();
    // No metric cards render in the error branch.
    expect(screen.queryByText(/total runs/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders skeleton cards (labels present, values hidden) while loading", () => {
    useDashboardStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    render(<KpiStrip />);
    // Labels are always present; the numeric values are replaced by skeletons.
    expect(screen.getByText(/total runs/i)).toBeInTheDocument();
    expect(screen.getByText(/needs review/i)).toBeInTheDocument();
  });
});
