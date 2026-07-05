"use client";

import { AlertTriangle, Loader2, ShieldCheck, Sparkles } from "lucide-react";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatConfidence } from "@/lib/format";
import { useAssistantAnalysis } from "@/lib/hooks/use-assistant";
import type { RunDetail } from "@/lib/api/types";

/**
 * AI Reviewer Assistant (Phase 21): an advisory second read of the extracted
 * output. On demand it performs a deterministic differential + keyword analysis
 * and surfaces potential clinical risks, a synthetic confidence, and a
 * suggestion. It is strictly advisory — it never approves, rejects, or mutates
 * the run — and it is hidden once a run is decided (review is redundant then).
 */
export function AiAssistantPanel({ run }: { run: RunDetail }) {
  const decided = run.status === "reviewed" || run.status === "rejected";
  const analysis = useAssistantAnalysis(run.id);

  // Advisory analysis is redundant once a human decision is recorded.
  if (decided) return null;

  const runAnalysis = () => {
    const editedOutput = (run.final_output ??
      run.parsed_output ??
      {}) as Record<string, unknown>;
    analysis.mutate(editedOutput);
  };

  const result = analysis.data;
  const hasRisks = !!result && result.clinical_risks.length > 0;

  return (
    <Card data-testid="ai-assistant-panel">
      <CardHeader className="flex flex-row items-center gap-2 space-y-0">
        <Sparkles className="h-4 w-4 text-primary" />
        <CardTitle className="text-base">AI reviewer assistant</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          An advisory second read of the extracted output. It flags potential
          clinical risks for your attention — it never approves or rejects.
        </p>

        <Button
          onClick={runAnalysis}
          disabled={analysis.isPending}
          data-testid="assistant-analyze-button"
        >
          {analysis.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {analysis.isPending ? "Analyzing…" : "Get AI analysis"}
        </Button>

        {analysis.isPending ? (
          <div data-testid="assistant-loading" className="space-y-2" aria-hidden>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : null}

        {analysis.isError ? (
          <p role="alert" className="text-sm text-destructive">
            Could not run analysis: {analysis.error.message}
          </p>
        ) : null}

        {result ? (
          <div data-testid="assistant-result" className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <StatusBadge
                tone={hasRisks ? "warning" : "success"}
                icon={hasRisks ? AlertTriangle : ShieldCheck}
              >
                {hasRisks ? "Risk alert" : "Stable"}
              </StatusBadge>
              <span className="text-xs text-muted-foreground">
                Assistant confidence{" "}
                <span className="font-semibold tabular-nums text-foreground">
                  {formatConfidence(result.confidence_score)}
                </span>
              </span>
            </div>

            {hasRisks ? (
              <div
                data-testid="assistant-risks"
                role="alert"
                className="space-y-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-3"
              >
                <h4 className="text-sm font-semibold text-foreground">
                  Potential clinical risks
                </h4>
                <ul className="list-inside list-disc space-y-1.5 text-sm text-foreground">
                  {result.clinical_risks.map((risk, i) => (
                    <li key={i}>{risk}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p
                data-testid="assistant-stable"
                className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-foreground"
              >
                No additional clinical concerns detected in the current output.
              </p>
            )}

            <p className="text-sm text-muted-foreground">{result.suggestion}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
