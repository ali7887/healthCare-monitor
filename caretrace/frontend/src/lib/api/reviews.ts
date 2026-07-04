import { apiPost } from "@/lib/api/client";
import type { ReviewActionRequest, ReviewActionResponse } from "@/lib/api/types";

export function postReviewAction(
  reviewId: string,
  body: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return apiPost<ReviewActionResponse>(`/reviews/${reviewId}/action`, body);
}
