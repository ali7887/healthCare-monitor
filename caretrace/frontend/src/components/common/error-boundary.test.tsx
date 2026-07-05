import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "@/components/common/error-boundary";
import { clearTelemetry, getEvents } from "@/lib/telemetry";

// React logs caught render errors to console.error; silence it so the expected
// throws don't clutter test output.
beforeEach(() => {
  clearTelemetry();
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

function Boom(): never {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  it("renders children when nothing throws", () => {
    render(
      <ErrorBoundary section="widget">
        <div data-testid="ok">healthy</div>
      </ErrorBoundary>
    );
    expect(screen.getByTestId("ok")).toBeInTheDocument();
  });

  it("shows an alert fallback naming the failed section when a child throws", () => {
    render(
      <ErrorBoundary section="the throughput trend">
        <Boom />
      </ErrorBoundary>
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/something went wrong loading the throughput trend/i);

    // The failure is recorded to telemetry (safe metadata only).
    const widgetError = getEvents().find((e) => e.name === "widget_error");
    expect(widgetError).toMatchObject({ status: "failure" });
    expect(widgetError?.meta).toMatchObject({ section: "the throughput trend" });
  });

  it("recovers via 'Try again' once the child stops throwing", async () => {
    let shouldThrow = true;
    function Flaky() {
      if (shouldThrow) throw new Error("kaboom");
      return <div data-testid="recovered">healthy</div>;
    }

    render(
      <ErrorBoundary section="widget">
        <Flaky />
      </ErrorBoundary>
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();

    shouldThrow = false;
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(screen.getByTestId("recovered")).toBeInTheDocument();
  });
});
