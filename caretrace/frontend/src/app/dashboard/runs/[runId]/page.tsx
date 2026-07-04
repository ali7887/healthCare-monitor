import { PageHeader } from "@/components/common/page-header";
import { RunDetailView } from "@/components/runs/run-detail";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return (
    <>
      <PageHeader
        title="Trace Viewer"
        subtitle="Full processing trace: input, extraction, validation, and routing."
      />
      <RunDetailView runId={runId} />
    </>
  );
}
