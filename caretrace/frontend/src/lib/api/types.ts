/** API types mirroring the healthCare-monitor backend (Phase 11 read models). */

export interface HealthStatus {
  status: string;
  service: string;
}

export type Provider = "openai" | "ollama";

export type RunStatus =
  | "auto_saved"
  | "needs_review"
  | "reviewed"
  | "rejected"
  | "failed";

export type RoutingDecision = "auto_save" | "human_review" | "reject";

export type Severity = "warning" | "critical";

export type IssueType = "schema" | "clinical" | "completeness" | "format";

export interface ValidationIssue {
  severity: Severity;
  issue_type: IssueType;
  field_path: string | null;
  message: string;
  rule_id: string | null;
}

export interface ConfidenceBreakdown {
  base_score: number;
  failure_penalties: number;
  retry_penalties: number;
  severity_penalties: number;
  type_penalties: number;
  raw_score: number;
  final_score: number;
}

export interface RunDetail {
  id: string;
  provider: Provider;
  status: RunStatus;
  transcript: string;
  parsed_output: Record<string, unknown> | null;
  final_output: Record<string, unknown> | null;
  confidence_score: number | null;
  confidence_breakdown: ConfidenceBreakdown | null;
  routing_decision: RoutingDecision | null;
  routing_reason: string | null;
  retry_count: number;
  warnings_count: number;
  latency_ms: number | null;
  cost: number | null;
  raw_model_response: string | null;
  issues: ValidationIssue[];
  created_at: string;
  pending_review_id: string | null;
}

export interface PaginatedRuns {
  items: RunDetail[];
  total: number;
  limit: number;
  offset: number;
}

export interface DashboardStats {
  total_runs: number;
  accepted_runs: number;
  routed_to_human_runs: number;
  rejected_runs: number;
  average_confidence: number;
}

export interface TimeseriesPoint {
  bucket: string; // ISO date
  auto_save: number;
  human_review: number;
  reject: number;
  total: number;
}

export interface DashboardTimeseries {
  bucket: string; // granularity, currently "day"
  points: TimeseriesPoint[];
}

export interface RunsQuery {
  limit?: number;
  offset?: number;
  routing_decision?: RoutingDecision;
  min_confidence?: number;
  max_confidence?: number;
}

export type ReviewStatus = "pending" | "approved" | "rejected";

export type ReviewAction = "approve" | "reject";

export interface ReviewActionRequest {
  action: ReviewAction;
  reviewer_notes?: string | null;
  edited_output?: Record<string, unknown> | null;
}

export interface ReviewActionResponse {
  id: string;
  run_id: string;
  status: ReviewStatus;
  run_status: RunStatus;
}
