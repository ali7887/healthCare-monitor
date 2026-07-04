import { PageHeader } from "@/components/common/page-header";
import { RefreshButton } from "@/components/common/refresh-button";
import { ErrorBoundary } from "@/components/common/error-boundary";
import { DashboardDebug } from "@/components/dashboard/dashboard-debug";
import { ThroughputTrendChart } from "@/components/dashboard/charts/throughput-trend-chart";
import { KpiStrip } from "@/components/dashboard/kpi-strip";
import { RecentRuns } from "@/components/dashboard/recent-runs";
import { RoutingDistribution } from "@/components/dashboard/routing-distribution";

export default function DashboardOverviewPage() {
  return (
    <>
      <PageHeader
        title="Dashboard Overview"
        subtitle="Aggregated reliability metrics across all processing runs."
        actions={<RefreshButton keys={[["dashboard"], ["runs"]]} />}
      />

      <ErrorBoundary section="the metrics strip">
        <KpiStrip />
      </ErrorBoundary>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ErrorBoundary section="recent runs">
            <RecentRuns />
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary section="the routing distribution">
            <RoutingDistribution />
          </ErrorBoundary>
        </div>
      </div>

      <ErrorBoundary section="the throughput trend">
        <ThroughputTrendChart />
      </ErrorBoundary>

      <DashboardDebug />
    </>
  );
}
