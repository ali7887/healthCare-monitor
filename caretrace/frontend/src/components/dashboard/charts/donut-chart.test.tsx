import { render, screen } from "@testing-library/react";
import { cloneElement, isValidElement, type ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

// Recharts' ResponsiveContainer measures its parent, which is 0x0 under jsdom,
// so the chart never gets dimensions. Mirror the real container by cloning the
// child chart with a fixed width/height so its SVG mounts deterministically.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      isValidElement(children)
        ? cloneElement(children as ReactElement<{ width: number; height: number }>, {
            width: 400,
            height: 200,
          })
        : children,
  };
});

import { DonutChart, type ChartSlice } from "@/components/dashboard/charts/donut-chart";

const SLICES: ChartSlice[] = [
  { label: "Auto-save", value: 6, color: "#10b981" },
  { label: "Human review", value: 3, color: "#f59e0b" },
  { label: "Reject", value: 1, color: "#f43f5e" },
];

describe("DonutChart", () => {
  it("renders the total and center label deterministically", () => {
    render(<DonutChart slices={SLICES} total={10} />);
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("total runs")).toBeInTheDocument();
  });

  it("honors a custom center label", () => {
    render(<DonutChart slices={SLICES} total={10} centerLabel="processed" />);
    expect(screen.getByText("processed")).toBeInTheDocument();
  });

  it("renders an SVG and does not crash with an all-zero (empty) dataset", () => {
    const { container } = render(
      <DonutChart
        slices={SLICES.map((s) => ({ ...s, value: 0 }))}
        total={0}
      />
    );
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
