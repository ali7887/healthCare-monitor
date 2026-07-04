"use client";

import { DebugPanel } from "@/components/dev/debug-panel";
import { ROUTING_SERIES } from "@/components/dashboard/charts/routing-series";
import { useDashboardStats } from "@/lib/hooks/use-dashboard-stats";
import { useDashboardTimeseries } from "@/lib/hooks/use-dashboard-timeseries";

/**
 * Dev-only: exposes the correctness state behind the dashboard charts — the raw
 * time-series payload, the shared routing-series mapping, and each query's
 * status — so drift between the donut (stats) and the trend (timeseries) is
 * visible at a glance. Renders nothing in production (see DebugPanel).
 */
export function DashboardDebug() {
  const stats = useDashboardStats();
  const timeseries = useDashboardTimeseries(14);

  return (
    <DebugPanel
      title="dashboard state"
      data={{
        routingSeries: ROUTING_SERIES.map(({ key, statKey, label }) => ({
          key,
          statKey,
          label,
        })),
        stats: { status: stats.status, data: stats.data ?? null },
        timeseries: {
          status: timeseries.status,
          points: timeseries.data?.points ?? [],
        },
      }}
    />
  );
}
