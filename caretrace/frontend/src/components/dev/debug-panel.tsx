"use client";

import { useState } from "react";

/**
 * Dev-only correctness overlay. Renders nothing in production builds (tree so
 * the JSON payloads never ship to users). In development it pins a collapsible
 * panel to the corner so you can eyeball the raw data behind a widget — the
 * time-series payload, the routing-series mapping, live mutation state — without
 * a network tab or a debugger.
 */
export function DebugPanel({
  title,
  data,
}: {
  title: string;
  data: Record<string, unknown>;
}) {
  const [open, setOpen] = useState(false);

  if (process.env.NODE_ENV === "production") return null;

  return (
    <div
      aria-hidden
      className="fixed bottom-3 right-3 z-50 max-w-[min(90vw,28rem)] font-mono text-[11px]"
    >
      <div className="overflow-hidden rounded-md border border-amber-500/40 bg-card/95 shadow-lg backdrop-blur">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-amber-600 dark:text-amber-400"
        >
          <span>🛠 {title}</span>
          <span className="text-muted-foreground">{open ? "hide" : "show"}</span>
        </button>
        {open ? (
          <pre className="max-h-[50vh] overflow-auto border-t px-3 py-2 text-muted-foreground">
            {JSON.stringify(data, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
