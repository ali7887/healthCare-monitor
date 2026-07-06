"use client";

import { ArrowLeft, FileText, Stethoscope } from "lucide-react";
import Link from "next/link";

import { ErrorState } from "@/components/common/states";
import {
  RoutingBadge,
  RunStatusBadge,
  StatusBadge,
} from "@/components/common/status-badge";
import { AiAssistantPanel } from "@/components/reviewer/ai-assistant-panel";
import { ReasoningPanel } from "@/components/runs/reasoning-panel";
import { ReviewActions } from "@/components/runs/review-actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { RunDetail as RunDetailModel } from "@/lib/api/types";
import {
  formatConfidence,
  formatCost,
  formatDateTime,
  formatLatency,
} from "@/lib/format";
import { useRun } from "@/lib/hooks/use-run";

interface Vital {
  value?: number | null;
  unit?: string | null;
}
interface BloodPressure {
  systolic?: number | null;
  diastolic?: number | null;
  unit?: string | null;
}
interface ClinicalNoteView {
  patient?: {
    name?: string | null;
    age?: number | null;
    sex?: string | null;
    patient_id?: string | null;
  } | null;
  vitals?: {
    blood_pressure?: BloodPressure | null;
    heart_rate?: Vital | null;
    temperature?: Vital | null;
    spo2?: Vital | null;
  } | null;
  medications?: Array<{
    name: string;
    dose?: string | null;
    route?: string | null;
    frequency?: string | null;
  }>;
  symptoms?: Array<{ text: string }>;
  observations?: Array<{ text: string }>;
  actions?: Array<{ text: string }>;
  follow_up?: Array<{ text: string }>;
  note_summary?: string | null;
  source_language?: string | null;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm font-medium text-foreground">{value ?? "—"}</dd>
    </div>
  );
}

function TextList({ items }: { items?: Array<{ text: string }> }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-muted-foreground">None documented.</p>;
  }
  return (
    <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
      {items.map((item, i) => (
        <li key={i}>{item.text}</li>
      ))}
    </ul>
  );
}

function ClinicalFields({ note }: { note: ClinicalNoteView }) {
  const bp = note.vitals?.blood_pressure;
  const vitals: Array<{ label: string; value: string }> = [];
  if (bp && (bp.systolic != null || bp.diastolic != null)) {
    vitals.push({
      label: "Blood pressure",
      value: `${bp.systolic ?? "—"}/${bp.diastolic ?? "—"} ${bp.unit ?? "mmHg"}`,
    });
  }
  if (note.vitals?.heart_rate?.value != null) {
    vitals.push({
      label: "Heart rate",
      value: `${note.vitals.heart_rate.value} ${note.vitals.heart_rate.unit ?? "bpm"}`,
    });
  }
  if (note.vitals?.temperature?.value != null) {
    vitals.push({
      label: "Temperature",
      value: `${note.vitals.temperature.value} °${note.vitals.temperature.unit ?? "C"}`,
    });
  }
  if (note.vitals?.spo2?.value != null) {
    vitals.push({
      label: "SpO₂",
      value: `${note.vitals.spo2.value}${note.vitals.spo2.unit ?? "%"}`,
    });
  }

  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Field label="Patient" value={note.patient?.name} />
        <Field label="Age" value={note.patient?.age} />
        <Field label="Sex" value={note.patient?.sex} />
        <Field label="Language" value={note.source_language} />
      </dl>

      {vitals.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {vitals.map((v) => (
            <div key={v.label} className="rounded-lg border bg-muted/30 p-3">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {v.label}
              </p>
              <p className="mt-1 text-sm font-semibold tabular-nums">{v.value}</p>
            </div>
          ))}
        </div>
      ) : null}

      <div>
        <h4 className="mb-2 text-sm font-semibold">Medications</h4>
        {note.medications && note.medications.length > 0 ? (
          <ul className="space-y-2">
            {note.medications.map((med, i) => (
              <li
                key={i}
                className="flex flex-wrap items-center gap-2 rounded-md border p-2.5 text-sm"
              >
                <span className="font-medium">{med.name}</span>
                {med.dose ? (
                  <StatusBadge tone="neutral">{med.dose}</StatusBadge>
                ) : (
                  <StatusBadge tone="warning">dose missing</StatusBadge>
                )}
                {med.route ? (
                  <span className="text-muted-foreground">{med.route}</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">None documented.</p>
        )}
      </div>

      <div className="grid gap-5 sm:grid-cols-3">
        <div>
          <h4 className="mb-2 text-sm font-semibold">Symptoms</h4>
          <TextList items={note.symptoms} />
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold">Observations</h4>
          <TextList items={note.observations} />
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold">Actions</h4>
          <TextList items={note.actions} />
        </div>
      </div>
    </div>
  );
}

function RawPanel({ title, content }: { title: string; content: string }) {
  return (
    <details className="rounded-lg border">
      <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
        {title}
      </summary>
      <pre className="max-h-96 overflow-auto border-t bg-muted/40 p-4 text-xs leading-relaxed">
        {content}
      </pre>
    </details>
  );
}

export function RunDetailView({ runId }: { runId: string }) {
  const { data: run, isLoading, isError, error, refetch } = useRun(runId);

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <Card>
        <ErrorState
          title={notFound ? "Run not found" : "Could not load run"}
          statusLabel={notFound ? "404 Not found" : "API unreachable"}
          description={
            notFound
              ? "This run does not exist or may have been removed."
              : "This run could not be loaded. Check that the backend is running, then retry."
          }
          onRetry={notFound ? undefined : () => refetch()}
        />
      </Card>
    );
  }

  if (isLoading || !run) {
    return <RunDetailSkeleton />;
  }

  const note = (run.parsed_output ?? null) as ClinicalNoteView | null;

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/runs"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Monitoring
      </Link>

      <RunHeader run={run} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <ReasoningPanel run={run} />
          <AiAssistantPanel run={run} />

          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Input transcript</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {run.transcript}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center gap-2 space-y-0">
              <Stethoscope className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Extracted clinical fields</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {note ? (
                <ClinicalFields note={note} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No structured output — extraction or schema validation failed.
                </p>
              )}
              <div className="space-y-3 pt-2">
                {run.parsed_output ? (
                  <RawPanel
                    title="Parsed output (JSON)"
                    content={JSON.stringify(run.parsed_output, null, 2)}
                  />
                ) : null}
                {run.raw_model_response ? (
                  <RawPanel
                    title="Raw model response"
                    content={run.raw_model_response}
                  />
                ) : null}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {run.status === "needs_review" ? <ReviewActions run={run} /> : null}
          <DecisionSummary run={run} />
          <ConfidenceBreakdownPanel run={run} />
          <ValidationChecks run={run} />
          <MetadataPanel run={run} />
        </div>
      </div>
    </div>
  );
}

function RunHeader({ run }: { run: RunDetailModel }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <p className="truncate font-mono text-sm text-muted-foreground">
            {run.id}
          </p>
          <p className="text-sm text-muted-foreground">
            Created {formatDateTime(run.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Route</span>
          <RoutingBadge decision={run.routing_decision} />
        </div>
      </CardContent>
    </Card>
  );
}

function DecisionSummary({ run }: { run: RunDetailModel }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Decision summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Routing</span>
          <RoutingBadge decision={run.routing_decision} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Confidence</span>
          <span className="text-sm font-semibold tabular-nums">
            {formatConfidence(run.confidence_score)}
          </span>
        </div>
        {run.routing_reason ? (
          <p className="rounded-md bg-muted/50 p-3 text-sm text-foreground">
            {run.routing_reason}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ConfidenceBreakdownPanel({ run }: { run: RunDetailModel }) {
  const b = run.confidence_breakdown;
  if (!b) return null;
  const rows: Array<{ label: string; value: number; negative?: boolean }> = [
    { label: "Base score", value: b.base_score },
    { label: "Failure penalties", value: b.failure_penalties, negative: true },
    { label: "Retry penalties", value: b.retry_penalties, negative: true },
    { label: "Severity penalties", value: b.severity_penalties, negative: true },
    { label: "Type penalties", value: b.type_penalties, negative: true },
    { label: "Final score", value: b.final_score },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Confidence breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-2 text-sm">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between">
              <dt className="text-muted-foreground">{row.label}</dt>
              <dd className="tabular-nums font-medium">
                {row.negative && row.value > 0 ? "−" : ""}
                {row.value.toFixed(2)}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function ValidationChecks({ run }: { run: RunDetailModel }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">Validation checks</CardTitle>
        <span className="text-xs text-muted-foreground">
          {run.issues.length} issue{run.issues.length === 1 ? "" : "s"}
        </span>
      </CardHeader>
      <CardContent>
        {run.issues.length === 0 ? (
          <StatusBadge tone="success">All checks passed</StatusBadge>
        ) : (
          <ul className="space-y-3">
            {run.issues.map((issue, i) => (
              <li key={i} className="space-y-1">
                <div className="flex items-center gap-2">
                  <StatusBadge
                    tone={issue.severity === "critical" ? "danger" : "warning"}
                  >
                    {issue.severity}
                  </StatusBadge>
                  <span className="text-xs text-muted-foreground">
                    {issue.issue_type}
                  </span>
                </div>
                <p className="text-sm text-foreground">{issue.message}</p>
                <p className="font-mono text-[11px] text-muted-foreground">
                  {issue.field_path ?? "—"}
                  {issue.rule_id ? ` · ${issue.rule_id}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function MetadataPanel({ run }: { run: RunDetailModel }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Run metadata</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4">
          <Field label="Provider" value={<span className="capitalize">{run.provider}</span>} />
          <Field label="Latency" value={formatLatency(run.latency_ms)} />
          <Field label="Est. cost" value={formatCost(run.cost)} />
          <Field label="Retries" value={run.retry_count} />
          <Field label="Warnings" value={run.warnings_count} />
          <Field label="Status" value={<RunStatusBadge status={run.status} />} />
        </dl>
      </CardContent>
    </Card>
  );
}

function RunDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-24 w-full" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    </div>
  );
}
