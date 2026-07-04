import { PageHeader } from "@/components/common/page-header";
import { RecentRuns } from "@/components/dashboard/recent-runs";

export default function TracePage() {
  return (
    <>
      <PageHeader
        title="Trace Viewer"
        subtitle="Select a run to inspect its full clinical processing trace."
      />
      <div className="max-w-2xl">
        <RecentRuns />
      </div>
    </>
  );
}
