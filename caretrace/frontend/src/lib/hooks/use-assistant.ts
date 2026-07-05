"use client";

import { useMutation } from "@tanstack/react-query";

import { analyzeReview } from "@/lib/api/assistant";
import type { AssistantAnalysis } from "@/lib/api/types";
import { recordEvent } from "@/lib/telemetry";

/**
 * Requests an advisory AI-assistant analysis for a run. This is a read-only
 * advisory call, so it deliberately invalidates no queries — it never changes
 * server state. Records telemetry around the trigger/success/failure so the dev
 * observability panel can summarize assistant activity.
 */
export function useAssistantAnalysis(runId: string) {
  return useMutation<AssistantAnalysis, Error, Record<string, unknown>>({
    mutationFn: (editedOutput) => analyzeReview(runId, editedOutput),
    onMutate: () => {
      recordEvent("assistant_analyze", { status: "start", meta: { runId } });
    },
    onSuccess: (data) => {
      recordEvent("assistant_analyze", {
        status: "success",
        meta: {
          runId,
          riskCount: data.clinical_risks.length,
          outcome: data.clinical_risks.length > 0 ? "risk_alert" : "stable",
        },
      });
    },
    onError: (error) => {
      recordEvent("assistant_analyze", {
        status: "failure",
        meta: { runId, error: error.message },
      });
    },
  });
}
