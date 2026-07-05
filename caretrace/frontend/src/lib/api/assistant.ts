import { apiPost } from "@/lib/api/client";
import type { AssistantAnalysis, AssistantAnalyzeRequest } from "@/lib/api/types";

/** Request an advisory AI-assistant analysis of a run's current output. */
export function analyzeReview(
  runId: string,
  editedOutput: Record<string, unknown>
): Promise<AssistantAnalysis> {
  const body: AssistantAnalyzeRequest = { edited_output: editedOutput };
  return apiPost<AssistantAnalysis>(`/runs/${runId}/analyze`, body);
}
