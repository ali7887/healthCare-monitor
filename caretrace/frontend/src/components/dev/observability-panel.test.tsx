import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { ObservabilityPanel } from "@/components/dev/observability-panel";
import { clearTelemetry, recordEvent } from "@/lib/telemetry";

beforeEach(() => {
  clearTelemetry();
});

describe("ObservabilityPanel", () => {
  it("renders recent telemetry: request ids, latencies, and assistant summary", async () => {
    recordEvent("api_request", {
      status: "success",
      durationMs: 12.5,
      requestId: "req-panel-1",
      meta: { method: "GET", path: "/dashboard/stats", statusCode: 200 },
    });
    recordEvent("assistant_analyze", {
      status: "success",
      meta: { runId: "run-1", outcome: "risk_alert", riskCount: 2 },
    });

    render(<ObservabilityPanel />);

    // Present but collapsed by default; expand it.
    expect(screen.getByTestId("observability-panel")).toBeInTheDocument();
    await userEvent.click(screen.getByText("show"));

    expect(screen.getByTestId("obs-env")).toHaveTextContent("test");
    expect(screen.getByTestId("obs-request-ids")).toHaveTextContent("req-panel-1");
    expect(screen.getByTestId("obs-latencies")).toHaveTextContent("/dashboard/stats");
    expect(screen.getByTestId("obs-latencies")).toHaveTextContent("12.5ms");
    expect(screen.getByTestId("obs-assistant")).toHaveTextContent("risk_alert");
    expect(screen.getByTestId("obs-events")).toHaveTextContent("assistant_analyze");
  });

  it("reflects events recorded after mount", async () => {
    render(<ObservabilityPanel />);
    await userEvent.click(screen.getByText("show"));
    expect(screen.getByTestId("obs-assistant")).toHaveTextContent("no calls yet");

    act(() => {
      recordEvent("assistant_analyze", {
        status: "failure",
        meta: { runId: "run-2", error: "Run not found" },
      });
    });

    expect(await screen.findByText(/Run not found/)).toBeInTheDocument();
  });
});
