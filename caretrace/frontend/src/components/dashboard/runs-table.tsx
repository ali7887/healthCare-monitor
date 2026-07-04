"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState, ErrorState } from "@/components/common/states";
import { RoutingBadge, RunStatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRuns } from "@/lib/hooks/use-runs";
import {
  formatConfidence,
  formatLatency,
  formatRelative,
  shortId,
} from "@/lib/format";
import type { RoutingDecision } from "@/lib/api/types";

const PAGE_SIZE = 10;

const ROUTING_FILTERS: Array<{ label: string; value: "" | RoutingDecision }> = [
  { label: "All decisions", value: "" },
  { label: "Auto-save", value: "auto_save" },
  { label: "Human review", value: "human_review" },
  { label: "Reject", value: "reject" },
];

export function RunsTable() {
  const [offset, setOffset] = useState(0);
  const [routing, setRouting] = useState<"" | RoutingDecision>("");

  const { data, isLoading, isError, refetch, isPlaceholderData } = useRuns({
    limit: PAGE_SIZE,
    offset,
    routing_decision: routing || undefined,
  });

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b p-4">
        <div className="text-sm text-muted-foreground">
          {isLoading ? "Loading…" : `${start}–${end} of ${total} runs`}
        </div>
        <select
          value={routing}
          onChange={(event) => {
            setRouting(event.target.value as "" | RoutingDecision);
            setOffset(0);
          }}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {ROUTING_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <CardContent className="p-0">
        {isError ? (
          <ErrorState
            title="Could not load runs"
            description="The runs list could not be loaded. Check that the backend is running, then retry."
            onRetry={() => refetch()}
          />
        ) : !isLoading && items.length === 0 ? (
          <EmptyState
            title="No runs match this filter"
            description="Try a different routing decision or clear the filter."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Run</th>
                  <th className="px-4 py-3 font-medium">Provider</th>
                  <th className="px-4 py-3 font-medium">Routing</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Latency</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? Array.from({ length: 6 }).map((_, index) => (
                      <tr key={index} className="border-b">
                        <td colSpan={8} className="px-4 py-3">
                          <Skeleton className="h-6 w-full" />
                        </td>
                      </tr>
                    ))
                  : items.map((run) => (
                      <tr
                        key={run.id}
                        className="border-b transition-colors hover:bg-accent/40"
                      >
                        <td className="px-4 py-3 font-mono text-xs">
                          {shortId(run.id)}
                        </td>
                        <td className="px-4 py-3 capitalize text-muted-foreground">
                          {run.provider}
                        </td>
                        <td className="px-4 py-3">
                          <RoutingBadge decision={run.routing_decision} />
                        </td>
                        <td className="px-4 py-3">
                          <RunStatusBadge status={run.status} />
                        </td>
                        <td className="px-4 py-3 tabular-nums">
                          {formatConfidence(run.confidence_score)}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-muted-foreground">
                          {formatLatency(run.latency_ms)}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {formatRelative(run.created_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link
                            href={`/dashboard/runs/${run.id}`}
                            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                          >
                            View
                            <ChevronRight className="h-3.5 w-3.5" />
                          </Link>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>

      <div className="flex items-center justify-end gap-2 border-t p-4">
        <Button
          variant="outline"
          size="sm"
          disabled={offset === 0 || isLoading}
          onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={isLoading || isPlaceholderData || end >= total}
          onClick={() => setOffset((value) => value + PAGE_SIZE)}
        >
          Next
        </Button>
      </div>
    </Card>
  );
}
