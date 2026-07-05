import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearTelemetry,
  getEvents,
  getLastRequestId,
  recordEvent,
  startSpan,
  subscribe,
} from "@/lib/telemetry";

beforeEach(() => {
  clearTelemetry();
});

describe("telemetry", () => {
  it("records success and failure events with metadata", () => {
    recordEvent("assistant_analyze", { status: "success", meta: { riskCount: 2 } });
    recordEvent("assistant_analyze", { status: "failure", meta: { error: "boom" } });

    const events = getEvents();
    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ name: "assistant_analyze", status: "success" });
    expect(events[0].meta).toEqual({ riskCount: 2 });
    expect(events[1].status).toBe("failure");
  });

  it("tracks the last request id from recorded events", () => {
    expect(getLastRequestId()).toBeUndefined();
    recordEvent("api_request", { status: "success", requestId: "req-abc" });
    expect(getLastRequestId()).toBe("req-abc");
  });

  it("caps the buffer so it never grows unbounded", () => {
    for (let i = 0; i < 80; i++) {
      recordEvent("api_request", { status: "success", meta: { i } });
    }
    const events = getEvents();
    expect(events.length).toBeLessThanOrEqual(50);
    // Oldest events are evicted; the newest is retained.
    expect(events[events.length - 1].meta).toEqual({ i: 79 });
  });

  it("notifies subscribers and can unsubscribe", () => {
    const listener = vi.fn();
    const unsubscribe = subscribe(listener);
    recordEvent("widget_error", { status: "failure" });
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    recordEvent("widget_error", { status: "failure" });
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("startSpan records a start then a timed completion", () => {
    const span = startSpan("run_detail_load", { runId: "run-1" });
    span.success({ requestId: "req-xyz" });

    const events = getEvents();
    expect(events.map((e) => e.status)).toEqual(["start", "success"]);
    const done = events[1];
    expect(typeof done.durationMs).toBe("number");
    expect(done.requestId).toBe("req-xyz");
    expect(done.meta).toEqual({ runId: "run-1" });
  });

  it("clearTelemetry resets the store", () => {
    recordEvent("api_request", { status: "success", requestId: "req-1" });
    clearTelemetry();
    expect(getEvents()).toEqual([]);
    expect(getLastRequestId()).toBeUndefined();
  });
});
