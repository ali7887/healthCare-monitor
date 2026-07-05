import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet, ApiError } from "@/lib/api/client";
import { clearTelemetry, getEvents, getLastRequestId } from "@/lib/telemetry";

function jsonResponse(
  body: unknown,
  { status = 200, requestId }: { status?: number; requestId?: string } = {}
): Response {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (requestId) headers.set("X-Request-ID", requestId);
  return new Response(JSON.stringify(body), { status, headers });
}

beforeEach(() => {
  clearTelemetry();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client telemetry", () => {
  it("captures the X-Request-ID from a response into telemetry", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ total_runs: 3 }, { requestId: "req-from-backend" })
    );

    const data = await apiGet<{ total_runs: number }>("/dashboard/stats");
    expect(data.total_runs).toBe(3);

    expect(getLastRequestId()).toBe("req-from-backend");
    const events = getEvents();
    const apiEvent = events.find((e) => e.name === "api_request");
    expect(apiEvent).toMatchObject({ status: "success", requestId: "req-from-backend" });
    expect(apiEvent?.meta).toMatchObject({ method: "GET", statusCode: 200 });
    expect(typeof apiEvent?.durationMs).toBe("number");
  });

  it("records a failure event and throws ApiError on a non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "Run not found" }, { status: 404, requestId: "req-404" })
    );

    await expect(apiGet("/runs/missing")).rejects.toBeInstanceOf(ApiError);
    const apiEvent = getEvents().find((e) => e.name === "api_request");
    expect(apiEvent).toMatchObject({ status: "failure", requestId: "req-404" });
    expect(apiEvent?.meta).toMatchObject({ statusCode: 404 });
  });

  it("records a failure event when fetch itself rejects", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));

    await expect(apiGet("/dashboard/stats")).rejects.toThrow("network down");
    const apiEvent = getEvents().find((e) => e.name === "api_request");
    expect(apiEvent?.status).toBe("failure");
    expect(apiEvent?.meta).toMatchObject({ error: "network down" });
  });
});
