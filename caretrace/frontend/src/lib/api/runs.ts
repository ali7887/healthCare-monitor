import { apiGet } from "@/lib/api/client";
import type { PaginatedRuns, RunDetail, RunsQuery } from "@/lib/api/types";

export function getRuns(query: RunsQuery = {}): Promise<PaginatedRuns> {
  return apiGet<PaginatedRuns>("/runs", {
    limit: query.limit,
    offset: query.offset,
    routing_decision: query.routing_decision,
    min_confidence: query.min_confidence,
    max_confidence: query.max_confidence,
  });
}

export function getRun(runId: string): Promise<RunDetail> {
  return apiGet<RunDetail>(`/runs/${runId}`);
}
