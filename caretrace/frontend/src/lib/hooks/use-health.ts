"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api/health";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: 0,
  });
}
