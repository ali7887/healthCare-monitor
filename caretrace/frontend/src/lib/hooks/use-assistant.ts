"use client";

import { useMutation } from "@tanstack/react-query";

import { analyzeReview } from "@/lib/api/assistant";
import type { AssistantAnalysis } from "@/lib/api/types";

/**
 * Requests an advisory AI-assistant analysis for a run. This is a read-only
 * advisory call, so it deliberately invalidates no queries — it never changes
 * server state.
 */
export function useAssistantAnalysis(runId: string) {
  return useMutation<AssistantAnalysis, Error, Record<string, unknown>>({
    mutationFn: (editedOutput) => analyzeReview(runId, editedOutput),
  });
}
