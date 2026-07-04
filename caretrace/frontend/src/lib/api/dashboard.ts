import { apiGet } from "@/lib/api/client";
import type { DashboardStats, DashboardTimeseries } from "@/lib/api/types";

export function getDashboardStats(): Promise<DashboardStats> {
  return apiGet<DashboardStats>("/dashboard/stats");
}

export function getDashboardTimeseries(
  days = 14
): Promise<DashboardTimeseries> {
  return apiGet<DashboardTimeseries>("/dashboard/stats/timeseries", {
    bucket: "day",
    days,
  });
}
