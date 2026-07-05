"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { postReviewAction } from "@/lib/api/reviews";
import type { ReviewAction } from "@/lib/api/types";
import { recordEvent } from "@/lib/telemetry";

export interface RunActionVars {
  reviewId: string;
  action: ReviewAction;
  reviewerNotes?: string;
  /** Corrected model output applied on approval; original stays in the trace. */
  editedOutput?: Record<string, unknown>;
}

/**
 * Applies a human review decision and invalidates the dashboard stats, runs
 * list/detail, and review queue so the UI reflects the new state.
 */
export function useRunAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reviewId, action, reviewerNotes, editedOutput }: RunActionVars) =>
      postReviewAction(reviewId, {
        action,
        reviewer_notes: reviewerNotes?.trim() ? reviewerNotes.trim() : null,
        edited_output: editedOutput ?? null,
      }),
    onMutate: ({ action, editedOutput }: RunActionVars) => {
      recordEvent("review_action", {
        status: "start",
        meta: { action, edited: editedOutput != null },
      });
    },
    onSuccess: (data) => {
      recordEvent("review_action", {
        status: "success",
        meta: { runStatus: data.run_status },
      });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
    onError: (error: Error) => {
      recordEvent("review_action", {
        status: "failure",
        meta: { error: error.message },
      });
    },
  });
}
