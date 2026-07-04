import { PageHeader } from "@/components/common/page-header";
import { RefreshButton } from "@/components/common/refresh-button";
import { RunsTable } from "@/components/dashboard/runs-table";

export default function RunsPage() {
  return (
    <>
      <PageHeader
        title="Monitoring"
        subtitle="Browse processing runs with routing filters and pagination."
        actions={<RefreshButton keys={[["runs"]]} />}
      />
      <RunsTable />
    </>
  );
}
