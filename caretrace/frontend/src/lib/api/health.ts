import { apiGet } from "@/lib/api/client";
import type { HealthStatus } from "@/lib/api/types";

export function getHealth(): Promise<HealthStatus> {
  return apiGet<HealthStatus>("/health");
}
