import type { DashboardStats, TimeseriesPoint } from "@/lib/api/types";

/**
 * Single source of truth for routing-outcome series (label + color) shared by
 * the distribution donut and the throughput trend chart. `statKey` maps to the
 * aggregate stats shape; `key` maps to a time-series point.
 */
export interface RoutingSeries {
  key: keyof Pick<TimeseriesPoint, "auto_save" | "human_review" | "reject">;
  statKey: keyof Pick<
    DashboardStats,
    "accepted_runs" | "routed_to_human_runs" | "rejected_runs"
  >;
  label: string;
  color: string;
}

export const ROUTING_SERIES: RoutingSeries[] = [
  { key: "auto_save", statKey: "accepted_runs", label: "Auto-save", color: "#10b981" },
  { key: "human_review", statKey: "routed_to_human_runs", label: "Human review", color: "#f59e0b" },
  { key: "reject", statKey: "rejected_runs", label: "Reject", color: "#f43f5e" },
];
