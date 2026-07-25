import { PageHeader } from "@/components/common/page-header";
import { EvaluationView } from "@/components/evaluation/evaluation-view";

export default function EvaluationPage() {
  return (
    <>
      <PageHeader
        title="Evaluation"
        subtitle="Reliability metrics per provider, with an exportable dataset for external analysis."
      />
      <EvaluationView />
    </>
  );
}
