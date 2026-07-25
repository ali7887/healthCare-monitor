"use client";

import { useQuery } from "@tanstack/react-query";

import { getEvaluation } from "@/lib/api/evaluation";

export function useEvaluation() {
  return useQuery({
    queryKey: ["evaluation"],
    queryFn: getEvaluation,
    staleTime: 30_000,
  });
}
