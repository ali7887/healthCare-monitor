"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Gauge,
  ListChecks,
  XCircle,
} from "lucide-react";

import { ErrorState } from "@/components/common/states";
import { StatCard } from "@/components/common/stat-card";
import { Card } from "@/components/ui/card";
import { useDashboardStats } from "@/lib/hooks/use-dashboard-stats";
import { formatConfidence, percent } from "@/lib/format";

export function KpiStrip() {
  const { data, isLoading, isError, refetch } = useDashboardStats();

  if (isError) {
    return (
      <Card>
        <ErrorState
          title="Unable to load dashboard metrics"
          description="Metrics could not be loaded. Check that the backend is running, then retry."
          onRetry={() => refetch()}
        />
      </Card>
    );
  }

  const total = data?.total_runs ?? 0;

  return (
    <div
      data-testid="kpi-strip"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5"
    >
      <StatCard
        label="Total Runs"
        value={data?.total_runs}
        hint="All processing runs"
        icon={ListChecks}
        tone="neutral"
        loading={isLoading}
      />
      <StatCard
        label="Auto-Saved"
        value={data?.accepted_runs}
        hint={data ? `${percent(data.accepted_runs, total)}% pass rate` : undefined}
        icon={CheckCircle2}
        tone="success"
        loading={isLoading}
      />
      <StatCard
        label="Needs Review"
        value={data?.routed_to_human_runs}
        hint={data ? `${percent(data.routed_to_human_runs, total)}% of runs` : undefined}
        icon={AlertTriangle}
        tone="warning"
        loading={isLoading}
      />
      <StatCard
        label="Rejected"
        value={data?.rejected_runs}
        hint={data ? `${percent(data.rejected_runs, total)}% of runs` : undefined}
        icon={XCircle}
        tone="danger"
        loading={isLoading}
      />
      <StatCard
        label="Avg. Confidence"
        value={data ? formatConfidence(data.average_confidence) : undefined}
        hint="Across all runs"
        icon={Gauge}
        tone="info"
        loading={isLoading}
      />
    </div>
  );
}
