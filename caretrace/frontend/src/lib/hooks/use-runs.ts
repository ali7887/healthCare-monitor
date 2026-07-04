"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getRuns } from "@/lib/api/runs";
import type { RunsQuery } from "@/lib/api/types";

export function useRuns(query: RunsQuery = {}) {
  return useQuery({
    queryKey: ["runs", query],
    queryFn: () => getRuns(query),
    placeholderData: keepPreviousData,
  });
}
