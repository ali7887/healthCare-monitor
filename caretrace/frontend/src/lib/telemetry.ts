/**
 * Local-first frontend telemetry for CareTrace.
 *
 * A tiny, in-memory event recorder — no external analytics SDK, no network, no
 * persistence. Events live in a capped ring buffer and are mirrored to the
 * console in development. The dev-only observability panel subscribes to this
 * store to surface recent activity, API latencies, and correlation ids.
 *
 * Designed to be trivially removable: nothing here changes app behavior, and
 * every call site is a one-liner. Record **safe metadata only** — never raw
 * clinical text or full payloads.
 */

export type TelemetryStatus = "start" | "success" | "failure" | "info";

export interface TelemetryEvent {
  /** Monotonic id, unique within the session. */
  id: number;
  /** Stable event name, e.g. "api_request", "assistant_analyze". */
  name: string;
  status: TelemetryStatus;
  /** Epoch milliseconds when recorded. */
  timestamp: number;
  /** Duration in ms for completed spans, when known. */
  durationMs?: number;
  /** Backend correlation id (X-Request-ID), when known. */
  requestId?: string;
  /** Small, safe metadata bag (ids, counts, statuses). */
  meta?: Record<string, unknown>;
}

export interface RecordOptions {
  status?: TelemetryStatus;
  durationMs?: number;
  requestId?: string;
  meta?: Record<string, unknown>;
}

const MAX_EVENTS = 50;

let seq = 0;
const events: TelemetryEvent[] = [];
const listeners = new Set<(events: TelemetryEvent[]) => void>();
let lastRequestId: string | undefined;

function notify(): void {
  const snapshot = getEvents();
  for (const listener of listeners) listener(snapshot);
}

/** Record a telemetry event. Returns the stored event. */
export function recordEvent(name: string, options: RecordOptions = {}): TelemetryEvent {
  const event: TelemetryEvent = {
    id: ++seq,
    name,
    status: options.status ?? "info",
    timestamp: Date.now(),
    durationMs: options.durationMs,
    requestId: options.requestId,
    meta: options.meta,
  };
  events.push(event);
  if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
  if (options.requestId) lastRequestId = options.requestId;

  if (process.env.NODE_ENV !== "production" && typeof console !== "undefined") {
    console.debug(`[telemetry] ${name}`, {
      status: event.status,
      durationMs: event.durationMs,
      requestId: event.requestId,
      ...event.meta,
    });
  }

  notify();
  return event;
}

/** Snapshot of recorded events, newest last. */
export function getEvents(): TelemetryEvent[] {
  return [...events];
}

/** The most recent backend correlation id observed from any API response. */
export function getLastRequestId(): string | undefined {
  return lastRequestId;
}

/** Subscribe to telemetry updates; returns an unsubscribe function. */
export function subscribe(listener: (events: TelemetryEvent[]) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Reset the store. Intended for tests and the dev panel's "clear" action. */
export function clearTelemetry(): void {
  events.length = 0;
  lastRequestId = undefined;
  seq = 0;
  notify();
}

function nowMs(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

export interface Span {
  /** Complete the span successfully, recording its duration. */
  success: (extra?: Pick<RecordOptions, "requestId" | "meta">) => TelemetryEvent;
  /** Complete the span as a failure, recording its duration. */
  failure: (extra?: Pick<RecordOptions, "requestId" | "meta">) => TelemetryEvent;
}

/**
 * Start a timed span. Emits a "start" event immediately and returns handles to
 * close it as success/failure with the measured duration attached.
 */
export function startSpan(name: string, meta?: Record<string, unknown>): Span {
  const started = nowMs();
  recordEvent(name, { status: "start", meta });
  const close = (status: TelemetryStatus) =>
    (extra?: Pick<RecordOptions, "requestId" | "meta">) =>
      recordEvent(name, {
        status,
        durationMs: Math.round((nowMs() - started) * 100) / 100,
        requestId: extra?.requestId,
        meta: { ...meta, ...extra?.meta },
      });
  return { success: close("success"), failure: close("failure") };
}
