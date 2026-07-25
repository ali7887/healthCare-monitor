"use client";

import { FlaskConical } from "lucide-react";

import { cn } from "@/lib/utils";
import { useHealth } from "@/lib/hooks/use-health";

export function ApiStatus() {
  const { data, isLoading, isError } = useHealth();
  const online = Boolean(data) && !isError;

  const label = isLoading
    ? "Checking API…"
    : online
      ? "API online"
      : "API unreachable";

  const tone = isLoading
    ? "bg-slate-400"
    : online
      ? "bg-emerald-500"
      : "bg-rose-500";

  return (
    <span className="inline-flex items-center gap-2">
      {online && data?.demo_mode ? (
        // Simulator mode is stated explicitly: extractions are deterministic
        // local simulations, not live model calls.
        <span
          data-testid="simulator-badge"
          title="Extractions are simulated locally — no model credentials configured. Validation, confidence, and routing run for real."
          className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-400"
        >
          <FlaskConical className="h-3 w-3" />
          Simulator mode
        </span>
      ) : null}
      <span className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground">
        <span className="relative flex h-2 w-2">
          {online ? (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
          ) : null}
          <span className={cn("relative inline-flex h-2 w-2 rounded-full", tone)} />
        </span>
        {label}
      </span>
    </span>
  );
}
