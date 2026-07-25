"use client";

import { useQuery } from "@tanstack/react-query";

import { searchRuns } from "@/lib/api/search";

/** Server-side run search; inactive until the query is at least 2 chars. */
export function useSearch(query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: ["search", trimmed],
    queryFn: () => searchRuns(trimmed),
    enabled: trimmed.length >= 2,
    staleTime: 15_000,
  });
}
