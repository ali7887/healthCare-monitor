import { describe, expect, it } from "vitest";

import { isNavActive } from "@/components/layout/nav";

describe("isNavActive", () => {
  it("marks Dashboard Overview active only on its exact route", () => {
    expect(isNavActive("/dashboard", "/dashboard")).toBe(true);
    expect(isNavActive("/dashboard/runs", "/dashboard")).toBe(false);
  });

  it("marks Monitoring active only on the runs list, not run details", () => {
    expect(isNavActive("/dashboard/runs", "/dashboard/runs")).toBe(true);
    expect(isNavActive("/dashboard/runs/abc-123", "/dashboard/runs")).toBe(false);
  });

  it("marks Trace Viewer active on its own route and on run detail pages", () => {
    expect(isNavActive("/dashboard/trace", "/dashboard/trace")).toBe(true);
    // A run detail page renders the Trace Viewer, so it owns the highlight.
    expect(isNavActive("/dashboard/runs/abc-123", "/dashboard/trace")).toBe(true);
    expect(isNavActive("/dashboard/runs", "/dashboard/trace")).toBe(false);
    expect(isNavActive("/dashboard", "/dashboard/trace")).toBe(false);
  });
});
