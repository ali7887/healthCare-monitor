"use client";

import { Activity } from "lucide-react";
import { useEffect, useState } from "react";

import {
  clearTelemetry,
  getEvents,
  subscribe,
  type TelemetryEvent,
} from "@/lib/telemetry";

/**
 * Dev-only observability surface. Subscribes to the local telemetry store and
 * surfaces recent runtime activity — API latencies, backend correlation ids,
 * the last assistant result, and the recent event stream — so demos and
 * debugging don't need the network tab.
 *
 * Hidden by default in production/demo builds; it can be explicitly enabled with
 * `NEXT_PUBLIC_OBSERVABILITY=1` (a safe, opt-in flag). It reads only in-memory
 * telemetry — no network, no persistence.
 */
export function ObservabilityPanel() {
  const enabled =
    process.env.NODE_ENV !== "production" ||
    process.env.NEXT_PUBLIC_OBSERVABILITY === "1";

  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<TelemetryEvent[]>([]);

  useEffect(() => {
    setEvents(getEvents());
    return subscribe(setEvents);
  }, []);

  if (!enabled) return null;

  const recent = [...events].reverse();
  const apiEvents = recent.filter(
    (e) => e.name === "api_request" && typeof e.durationMs === "number"
  );
  const requestIds = Array.from(
    new Set(recent.map((e) => e.requestId).filter(Boolean))
  ).slice(0, 3) as string[];
  const lastAssistant = recent.find(
    (e) => e.name === "assistant_analyze" && e.status !== "start"
  );
  const mode = process.env.NODE_ENV;

  return (
    <div
      data-testid="observability-panel"
      className="fixed bottom-3 left-3 z-50 max-w-[min(90vw,24rem)] font-mono text-[11px]"
    >
      <div className="overflow-hidden rounded-md border border-sky-500/40 bg-card/95 shadow-lg backdrop-blur">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-sky-600 dark:text-sky-400"
        >
          <span className="flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5" />
            observability
          </span>
          <span className="text-muted-foreground">{open ? "hide" : "show"}</span>
        </button>

        {open ? (
          <div className="max-h-[60vh] space-y-3 overflow-auto border-t px-3 py-2 text-muted-foreground">
            <dl className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1">
              <dt>env</dt>
              <dd data-testid="obs-env" className="text-foreground">
                {mode}
              </dd>
              <dt>events</dt>
              <dd className="text-foreground">{events.length}</dd>
              <dt>last req id</dt>
              <dd className="truncate text-foreground">{requestIds[0] ?? "—"}</dd>
            </dl>

            <section>
              <h4 className="mb-1 font-semibold text-foreground">
                recent request ids
              </h4>
              {requestIds.length ? (
                <ul className="space-y-0.5" data-testid="obs-request-ids">
                  {requestIds.map((id) => (
                    <li key={id} className="truncate">
                      {id}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>none yet</p>
              )}
            </section>

            <section>
              <h4 className="mb-1 font-semibold text-foreground">api latency</h4>
              {apiEvents.length ? (
                <ul className="space-y-0.5" data-testid="obs-latencies">
                  {apiEvents.slice(0, 6).map((e) => (
                    <li key={e.id} className="flex justify-between gap-2">
                      <span className="truncate">
                        {String((e.meta?.method as string) ?? "")}{" "}
                        {String((e.meta?.path as string) ?? "")}
                      </span>
                      <span className="tabular-nums text-foreground">
                        {e.durationMs}ms
                        {e.status === "failure" ? " ⚠" : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>none yet</p>
              )}
            </section>

            <section>
              <h4 className="mb-1 font-semibold text-foreground">assistant</h4>
              <p data-testid="obs-assistant">
                {lastAssistant
                  ? `${lastAssistant.status} · ${String(
                      lastAssistant.meta?.outcome ?? lastAssistant.meta?.error ?? "—"
                    )}`
                  : "no calls yet"}
              </p>
            </section>

            <section>
              <h4 className="mb-1 font-semibold text-foreground">event stream</h4>
              <ul className="space-y-0.5" data-testid="obs-events">
                {recent.slice(0, 8).map((e) => (
                  <li key={e.id} className="flex justify-between gap-2">
                    <span className="truncate">
                      {e.name}
                      <span className="text-sky-600 dark:text-sky-400">
                        {" "}
                        {e.status}
                      </span>
                    </span>
                    {typeof e.durationMs === "number" ? (
                      <span className="tabular-nums">{e.durationMs}ms</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>

            <button
              type="button"
              onClick={() => clearTelemetry()}
              className="text-muted-foreground underline underline-offset-2 hover:text-foreground"
            >
              clear
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
