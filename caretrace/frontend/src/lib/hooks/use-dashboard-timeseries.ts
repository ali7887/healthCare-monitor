"use client";

import { useQuery } from "@tanstack/react-query";

import { getDashboardTimeseries } from "@/lib/api/dashboard";

export function useDashboardTimeseries(days = 14) {
  return useQuery({
    // keyed under ["dashboard"] so the dashboard Refresh button invalidates it
    queryKey: ["dashboard", "timeseries", days],
    queryFn: () => getDashboardTimeseries(days),
  });
}
