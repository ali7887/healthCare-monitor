/** Evaluation dashboard API. */

import { API_BASE_URL, apiGet } from "@/lib/api/client";
import type { EvaluationSummary } from "@/lib/api/types";

export async function getEvaluation(): Promise<EvaluationSummary> {
  return apiGet<EvaluationSummary>("/evaluation");
}

/** Direct download URL — the backend sets Content-Disposition: attachment. */
export function evaluationExportUrl(format: "json" | "csv"): string {
  return `${API_BASE_URL}/evaluation/export?format=${format}`;
}
