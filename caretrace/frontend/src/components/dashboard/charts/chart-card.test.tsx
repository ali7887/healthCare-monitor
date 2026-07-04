import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChartCard } from "@/components/dashboard/charts/chart-card";

describe("ChartCard state machine", () => {
  it("renders children when idle (no loading/error/empty)", () => {
    render(
      <ChartCard title="Routing distribution">
        <div data-testid="chart-body">chart</div>
      </ChartCard>
    );
    expect(screen.getByTestId("chart-body")).toBeInTheDocument();
  });

  it("shows the error state and wires up retry, hiding children", async () => {
    const onRetry = vi.fn();
    render(
      <ChartCard title="Routing distribution" isError onRetry={onRetry}>
        <div data-testid="chart-body">chart</div>
      </ChartCard>
    );

    expect(screen.queryByTestId("chart-body")).not.toBeInTheDocument();
    expect(
      screen.getByText("Could not load routing distribution")
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("prefers the error state over loading when both are set", () => {
    render(<ChartCard title="Trend" isError loading isEmpty />);
    expect(screen.getByText("Could not load trend")).toBeInTheDocument();
  });

  it("shows the empty state (not children) when empty", () => {
    render(
      <ChartCard title="Trend" isEmpty emptyTitle="No runs yet">
        <div data-testid="chart-body">chart</div>
      </ChartCard>
    );
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-body")).not.toBeInTheDocument();
  });
});
