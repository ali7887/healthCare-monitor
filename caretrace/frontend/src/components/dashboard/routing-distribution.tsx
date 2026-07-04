"use client";

import dynamic from "next/dynamic";

import { ChartCard } from "@/components/dashboard/charts/chart-card";
import { ChartLegend, type LegendItem } from "@/components/dashboard/charts/chart-legend";
import type { ChartSlice } from "@/components/dashboard/charts/donut-chart";
import { ROUTING_SERIES } from "@/components/dashboard/charts/routing-series";
import { useDashboardStats } from "@/lib/hooks/use-dashboard-stats";
import { percent } from "@/lib/format";

// Recharts loaded on demand (see throughput-trend-chart for rationale).
const DonutChart = dynamic(
  () =>
    import("@/components/dashboard/charts/donut-chart").then((m) => m.DonutChart),
  {
    ssr: false,
    loading: () => <div className="mx-auto h-48 w-full animate-pulse rounded-md bg-muted" />,
  }
);

export function RoutingDistribution() {
  const { data, isLoading, isError, refetch } = useDashboardStats();
  const total = data?.total_runs ?? 0;

  // Data mapping: aggregate stats -> chart slices + legend items.
  const slices: ChartSlice[] = ROUTING_SERIES.map((seg) => ({
    label: seg.label,
    value: data?.[seg.statKey] ?? 0,
    color: seg.color,
  }));
  const legend: LegendItem[] = slices.map((slice) => ({
    ...slice,
    percent: percent(slice.value, total),
  }));

  return (
    <ChartCard
      title="Routing distribution"
      testId="routing-distribution"
      loading={isLoading}
      isError={isError}
      onRetry={() => refetch()}
      isEmpty={total === 0}
      emptyTitle="No routing data"
      emptyDescription="Distribution appears once runs have been processed."
    >
      <div className="space-y-5">
        <DonutChart slices={slices} total={total} />
        <ChartLegend items={legend} />
      </div>
    </ChartCard>
  );
}
