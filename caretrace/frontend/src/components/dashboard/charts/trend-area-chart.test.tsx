import { render } from "@testing-library/react";
import { cloneElement, isValidElement, type ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      isValidElement(children)
        ? cloneElement(children as ReactElement<{ width: number; height: number }>, {
            width: 600,
            height: 260,
          })
        : children,
  };
});

import { TrendAreaChart } from "@/components/dashboard/charts/trend-area-chart";
import type { TimeseriesPoint } from "@/lib/api/types";

function point(bucket: string, over: Partial<TimeseriesPoint> = {}): TimeseriesPoint {
  const base = { bucket, auto_save: 0, human_review: 0, reject: 0, total: 0 };
  const merged = { ...base, ...over };
  merged.total = merged.auto_save + merged.human_review + merged.reject;
  return merged;
}

describe("TrendAreaChart", () => {
  it("mounts an SVG for a populated series", () => {
    const points = [
      point("2026-07-01", { auto_save: 3, reject: 1 }),
      point("2026-07-02", { human_review: 2 }),
      point("2026-07-03", { auto_save: 5 }),
    ];
    const { container } = render(<TrendAreaChart points={points} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders one stacked area per routing series", () => {
    const points = [point("2026-07-01", { auto_save: 1, human_review: 1, reject: 1 })];
    const { container } = render(<TrendAreaChart points={points} />);
    // Recharts tags each <Area> layer with the recharts-area class.
    expect(container.querySelectorAll(".recharts-area").length).toBe(3);
  });

  it("does not crash on an empty series (zero-run window)", () => {
    const { container } = render(<TrendAreaChart points={[]} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
