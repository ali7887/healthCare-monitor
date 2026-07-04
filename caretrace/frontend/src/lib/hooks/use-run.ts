"use client";

import { useQuery } from "@tanstack/react-query";

import { getRun } from "@/lib/api/runs";

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["runs", "detail", runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
  });
}
