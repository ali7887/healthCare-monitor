/** Minimal typed fetch client for the healthCare-monitor backend. */

import { recordEvent } from "@/lib/telemetry";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

/** Backend correlation header — echoed by RequestContextMiddleware. */
const REQUEST_ID_HEADER = "X-Request-ID";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type QueryValue = string | number | boolean | undefined | null;

function buildQuery(params?: Record<string, QueryValue>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

function nowMs(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

/**
 * Single request path shared by GET/POST. Records one `api_request` telemetry
 * event per call — with the measured latency and the backend correlation id
 * (read from the `X-Request-ID` response header) — so the dev observability
 * panel can tie a frontend action back to the exact backend logs.
 */
async function request<T>(
  method: "GET" | "POST",
  path: string,
  init: RequestInit
): Promise<T> {
  const started = nowMs();
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { cache: "no-store", ...init });
  } catch (error) {
    recordEvent("api_request", {
      status: "failure",
      durationMs: Math.round((nowMs() - started) * 100) / 100,
      meta: { method, path, error: (error as Error).message },
    });
    throw error;
  }

  const requestId = response.headers.get(REQUEST_ID_HEADER) ?? undefined;
  recordEvent("api_request", {
    status: response.ok ? "success" : "failure",
    durationMs: Math.round((nowMs() - started) * 100) / 100,
    requestId,
    meta: { method, path, statusCode: response.status },
  });

  return parse<T>(response);
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, QueryValue>
): Promise<T> {
  return request<T>("GET", `${path}${buildQuery(params)}`, {
    headers: { Accept: "application/json" },
  });
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>("POST", path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}
