"use client";

import { Download, FileJson, Gauge, ListChecks, RotateCcw, ShieldCheck } from "lucide-react";

import { ErrorState } from "@/components/common/states";
import { StatCard } from "@/components/common/stat-card";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { evaluationExportUrl } from "@/lib/api/evaluation";
import { useEvaluation } from "@/lib/hooks/use-evaluation";
import {
  formatConfidence,
  formatCost,
  formatLatency,
  formatProvider,
  percent,
} from "@/lib/format";

/**
 * Evaluation dashboard: reliability metrics per provider plus a downloadable
 * dataset for external analysis (LangSmith / W&B-style tooling ingests the
 * JSON or CSV directly). Read-only; all numbers come from stored run traces.
 */
export function EvaluationView() {
  const { data, isLoading, isError, refetch } = useEvaluation();

  if (isError) {
    return (
      <Card>
        <ErrorState
          title="Unable to load evaluation metrics"
          description="Metrics could not be loaded. Check that the backend is running, then retry."
          onRetry={() => refetch()}
        />
      </Card>
    );
  }

  const totals = data?.totals;
  const total = totals?.runs ?? 0;
  const reviewShare = totals ? totals.needs_review + totals.reviewed : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Runs evaluated"
          value={totals?.runs}
          hint="All stored processing runs"
          icon={ListChecks}
          tone="neutral"
          loading={isLoading}
        />
        <StatCard
          label="Auto-save rate"
          value={totals ? `${percent(totals.auto_saved, total)}%` : undefined}
          hint="Passed every deterministic check"
          icon={ShieldCheck}
          tone="success"
          loading={isLoading}
        />
        <StatCard
          label="Review rate"
          value={totals ? `${percent(reviewShare, total)}%` : undefined}
          hint="Routed to a human (incl. decided)"
          icon={Gauge}
          tone="warning"
          loading={isLoading}
        />
        <StatCard
          label="Failed extractions"
          value={totals?.failed}
          hint="No valid structured note"
          icon={RotateCcw}
          tone="danger"
          loading={isLoading}
        />
      </div>

      <Card data-testid="provider-comparison">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Provider comparison</CardTitle>
          <div className="flex items-center gap-2">
            {/* Plain download links: the backend answers with
                Content-Disposition: attachment, so the browser saves a file. */}
            <a
              href={evaluationExportUrl("json")}
              data-testid="export-json"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            >
              <FileJson className="h-4 w-4" />
              Export evaluation run (JSON)
            </a>
            <a
              href={evaluationExportUrl("csv")}
              data-testid="export-csv"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
            >
              <Download className="h-4 w-4" />
              CSV
            </a>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : (data?.by_provider.length ?? 0) === 0 ? (
            <p className="px-4 pb-4 text-sm text-muted-foreground">
              No runs yet — metrics appear once transcripts have been processed.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-medium">Provider</th>
                    <th className="px-4 py-3 font-medium">Runs</th>
                    <th className="px-4 py-3 font-medium">Auto-save rate</th>
                    <th className="px-4 py-3 font-medium">Retry rate</th>
                    <th className="px-4 py-3 font-medium">Avg. confidence</th>
                    <th className="px-4 py-3 font-medium">Avg. latency</th>
                    <th className="px-4 py-3 font-medium">Est. cost</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.by_provider.map((row) => (
                    <tr key={row.provider} className="border-b last:border-b-0">
                      <td className="px-4 py-3 font-medium text-foreground">
                        {formatProvider(row.provider)}
                      </td>
                      <td className="px-4 py-3 tabular-nums">{row.runs}</td>
                      <td className="px-4 py-3 tabular-nums">
                        {Math.round(row.auto_save_rate * 100)}%
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {Math.round(row.retry_rate * 100)}%
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatConfidence(row.avg_confidence)}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-muted-foreground">
                        {formatLatency(row.avg_latency_ms)}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-muted-foreground">
                        {formatCost(row.estimated_cost_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
