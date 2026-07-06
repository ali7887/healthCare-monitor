"use client";

import { ChevronRight, ListChecks } from "lucide-react";
import Link from "next/link";

import { EmptyState, ErrorState } from "@/components/common/states";
import { RoutingBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRuns } from "@/lib/hooks/use-runs";
import { formatConfidence, formatRelative, shortId } from "@/lib/format";

export function RecentRuns() {
  // Eight rows keeps the card roughly level with the routing donut beside it,
  // instead of leaving a band of empty page under the shorter column.
  const { data, isLoading, isError, refetch } = useRuns({ limit: 8 });
  const items = data?.items ?? [];

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">Recent runs</CardTitle>
        <Link
          href="/dashboard/runs"
          className="text-xs font-medium text-primary hover:underline"
        >
          View all
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {isError ? (
          <ErrorState
            title="Could not load recent runs"
            onRetry={() => refetch()}
          />
        ) : isLoading ? (
          <div className="space-y-1 p-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={ListChecks}
            title="No runs yet"
            description="Processed runs will appear here once the pipeline handles a transcript."
          />
        ) : (
          <ul className="divide-y">
            {items.map((run) => (
              <li key={run.id}>
                <Link
                  href={`/dashboard/runs/${run.id}`}
                  className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/50"
                >
                  <span className="font-mono text-xs text-muted-foreground">
                    {shortId(run.id)}
                  </span>
                  <div className="ml-1">
                    <RoutingBadge decision={run.routing_decision} />
                  </div>
                  <span className="ml-auto tabular-nums text-sm text-foreground">
                    {formatConfidence(run.confidence_score)}
                  </span>
                  <span className="hidden w-20 text-right text-xs text-muted-foreground sm:block">
                    {formatRelative(run.created_at)}
                  </span>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
