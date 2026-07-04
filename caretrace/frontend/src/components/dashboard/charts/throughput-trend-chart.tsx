"use client";

import dynamic from "next/dynamic";

import { ChartCard } from "@/components/dashboard/charts/chart-card";
import { ChartLegend, type LegendItem } from "@/components/dashboard/charts/chart-legend";
import { ROUTING_SERIES } from "@/components/dashboard/charts/routing-series";
import { percent } from "@/lib/format";
import { useDashboardTimeseries } from "@/lib/hooks/use-dashboard-timeseries";

// Recharts is the heaviest client module; load it on demand so it stays out of
// the initial dashboard bundle. The container's skeleton covers the brief load.
const TrendAreaChart = dynamic(
  () =>
    import("@/components/dashboard/charts/trend-area-chart").then(
      (m) => m.TrendAreaChart
    ),
  {
    ssr: false,
    loading: () => <div className="h-64 w-full animate-pulse rounded-md bg-muted" />,
  }
);

const WINDOW_DAYS = 14;

export function ThroughputTrendChart() {
  const { data, isLoading, isError, refetch } = useDashboardTimeseries(WINDOW_DAYS);
  const points = data?.points ?? [];
  const windowTotal = points.reduce((sum, point) => sum + point.total, 0);

  // Summary legend: window totals per routing outcome.
  const legend: LegendItem[] = ROUTING_SERIES.map((series) => {
    const value = points.reduce((sum, point) => sum + point[series.key], 0);
    return {
      label: series.label,
      value,
      percent: percent(value, windowTotal),
      color: series.color,
    };
  });

  return (
    <ChartCard
      title="Throughput over time"
      testId="throughput-trend"
      description={`Runs processed per day (last ${WINDOW_DAYS} days)`}
      loading={isLoading}
      isError={isError}
      onRetry={() => refetch()}
      isEmpty={windowTotal === 0}
      emptyTitle={`No runs in the last ${WINDOW_DAYS} days`}
      emptyDescription="Processed runs will chart here as they arrive."
    >
      <div className="space-y-5">
        <TrendAreaChart points={points} />
        <ChartLegend items={legend} />
      </div>
    </ChartCard>
  );
}
