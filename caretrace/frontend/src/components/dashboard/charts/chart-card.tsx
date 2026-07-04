import type { ReactNode } from "react";

import { EmptyState, ErrorState } from "@/components/common/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Presenter shell for any dashboard chart. Owns the loading / error / empty
 * state machinery so individual charts (donut today, time-series later) only
 * supply data mapping + rendering. This keeps the chart area extensible without
 * a rewrite when trend charts are added.
 */
export function ChartCard({
  title,
  description,
  loading = false,
  isError = false,
  onRetry,
  isEmpty = false,
  emptyTitle = "No data",
  emptyDescription,
  children,
  testId,
}: {
  title: string;
  description?: string;
  loading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  children?: ReactNode;
  /** Optional stable hook for E2E tests. */
  testId?: string;
}) {
  return (
    <Card className="h-full" data-testid={testId}>
      <CardHeader className="space-y-1">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? (
          <p className="text-xs text-muted-foreground">{description}</p>
        ) : null}
      </CardHeader>
      <CardContent>
        {isError ? (
          <ErrorState
            title={`Could not load ${title.toLowerCase()}`}
            onRetry={onRetry}
          />
        ) : loading ? (
          <div className="space-y-4">
            <Skeleton className="mx-auto h-40 w-40 rounded-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : isEmpty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
