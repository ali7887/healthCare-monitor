"use client";

import { History } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime, formatProvider } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { RunDetail } from "@/lib/api/types";

type Tone = "neutral" | "warning" | "danger" | "success" | "info";

interface AuditEvent {
  label: string;
  detail?: string | null;
  at: string; // ISO timestamp
  tone: Tone;
}

const TONE_DOT: Record<Tone, string> = {
  neutral: "bg-slate-400",
  info: "bg-blue-500",
  warning: "bg-amber-500",
  danger: "bg-rose-500",
  success: "bg-emerald-500",
};

/**
 * Derive the chronological human + AI action timeline from the stored trace.
 * AI-phase events share the run's creation timestamp (the pipeline completes
 * within one request); the human decision carries its own recorded time.
 */
function buildEvents(run: RunDetail): AuditEvent[] {
  const events: AuditEvent[] = [];
  const created = run.created_at;

  if (run.status === "failed") {
    events.push({
      label: `Extraction by ${formatProvider(run.provider)} failed`,
      detail: "No valid structured note was produced.",
      at: created,
      tone: "danger",
    });
  } else {
    events.push({
      label: `Parsed by AI (${formatProvider(run.provider)})`,
      detail: "Structured documentation extracted from the transcript.",
      at: created,
      tone: "info",
    });
  }

  if (run.retry_count > 0) {
    events.push({
      label: `Self-correction retry used (${run.retry_count}×)`,
      detail: "Validation feedback was fed back for one corrective attempt.",
      at: created,
      tone: "warning",
    });
  }

  for (const issue of run.issues) {
    events.push({
      label: `Flagged: ${issue.message}`,
      detail: issue.field_path
        ? `${issue.rule_id ?? issue.issue_type} · ${issue.field_path}`
        : (issue.rule_id ?? issue.issue_type),
      at: created,
      tone: issue.severity === "critical" ? "danger" : "warning",
    });
  }

  if (run.routing_decision) {
    const routingLabel = {
      auto_save: "Routed: Auto-save",
      human_review: "Routed: Human review",
      reject: "Routed: Reject",
    }[run.routing_decision];
    events.push({
      label: routingLabel,
      detail: run.routing_reason,
      at: created,
      tone: run.routing_decision === "auto_save" ? "success" : "neutral",
    });
  }

  if (run.reviewed_at && (run.status === "reviewed" || run.status === "rejected")) {
    const edited =
      run.status === "reviewed" &&
      run.final_output !== null &&
      JSON.stringify(run.final_output) !== JSON.stringify(run.parsed_output);
    events.push({
      label:
        run.status === "reviewed"
          ? edited
            ? "Modified and approved by reviewer"
            : "Approved by reviewer"
          : "Rejected by reviewer",
      detail: run.reviewer_notes,
      at: run.reviewed_at,
      tone: run.status === "reviewed" ? "success" : "danger",
    });
    events.push({
      label: `Status updated to ${run.status === "reviewed" ? "Reviewed" : "Rejected"}`,
      at: run.reviewed_at,
      tone: "neutral",
    });
  }

  return events;
}

/**
 * Audit Trail: a scannable timeline of every AI and human action on this run,
 * with timestamps — traceability and accountability at a glance.
 */
export function AuditTrail({ run }: { run: RunDetail }) {
  const events = buildEvents(run);

  return (
    <Card data-testid="audit-trail">
      <CardHeader className="flex flex-row items-center gap-2 space-y-0">
        <History className="h-4 w-4 text-muted-foreground" />
        <CardTitle className="text-base">Audit trail</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="relative space-y-0">
          {events.map((event, index) => (
            <li key={index} className="relative flex gap-3.5 pb-5 last:pb-0">
              {/* Connector line between dots (not after the final event). */}
              {index < events.length - 1 ? (
                <span
                  aria-hidden
                  className="absolute left-[5px] top-4 h-full w-px bg-border"
                />
              ) : null}
              <span
                aria-hidden
                className={cn(
                  "relative mt-1.5 h-[11px] w-[11px] shrink-0 rounded-full ring-4 ring-card",
                  TONE_DOT[event.tone]
                )}
              />
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                  <p className="text-sm font-medium text-foreground">{event.label}</p>
                  <time className="font-mono text-[11px] text-muted-foreground">
                    {formatDateTime(event.at)}
                  </time>
                </div>
                {event.detail ? (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {event.detail}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
