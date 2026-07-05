"use client";

import { Check, Loader2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useRunAction } from "@/lib/hooks/use-run-action";
import type { ReviewAction, RunDetail } from "@/lib/api/types";

type ParseResult =
  | { ok: true; value: Record<string, unknown> }
  | { ok: false; error: string };

function parseEditedOutput(text: string): ParseResult {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    return { ok: false, error: "Invalid JSON — fix the syntax before approving." };
  }
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return { ok: false, error: "Edited output must be a JSON object." };
  }
  return { ok: true, value: value as Record<string, unknown> };
}

export function ReviewActions({ run }: { run: RunDetail }) {
  // The run detail now carries its pending review id directly (Phase 15).
  const reviewId = run.pending_review_id;
  const action = useRunAction();

  const originalJson = useMemo(
    () => JSON.stringify(run.parsed_output ?? {}, null, 2),
    [run.parsed_output]
  );

  const [notes, setNotes] = useState("");
  const [editing, setEditing] = useState(false);
  const [editedJson, setEditedJson] = useState(originalJson);
  const [jsonError, setJsonError] = useState<string | null>(null);

  const dirty = editing && editedJson !== originalJson;

  const submit = (decision: ReviewAction) => {
    if (!reviewId) return;
    setJsonError(null);

    if (decision === "approve" && editing) {
      const parsed = parseEditedOutput(editedJson);
      if (!parsed.ok) {
        setJsonError(parsed.error);
        return;
      }
      action.mutate({
        reviewId,
        action: "approve",
        reviewerNotes: notes,
        editedOutput: parsed.value,
      });
      return;
    }

    action.mutate({ reviewId, action: decision, reviewerNotes: notes });
  };

  const busy = action.isPending;

  return (
    <Card className="border-primary/30" data-testid="review-actions">
      <CardHeader>
        <CardTitle className="text-base">Human review</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!reviewId ? (
          <p className="text-sm text-muted-foreground">
            No pending review item is associated with this run.
          </p>
        ) : action.isSuccess ? (
          <div
            data-testid="review-success"
            role="status"
            aria-live="polite"
            className="flex items-center gap-2"
          >
            <StatusBadge tone="success" icon={Check}>
              Decision recorded
            </StatusBadge>
            <span className="text-sm text-muted-foreground">
              Run marked as {action.data.run_status.replace("_", " ")}.
            </span>
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Confirm the extracted documentation or route it out. This decision
              updates the run and clears the review queue item.
            </p>

            <div className="space-y-1.5">
              <label
                htmlFor="reviewer-notes"
                className="text-xs font-medium text-foreground"
              >
                Reviewer notes (optional)
              </label>
              <Textarea
                id="reviewer-notes"
                data-testid="reviewer-notes-input"
                placeholder="Add context for this decision…"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                disabled={busy}
              />
            </div>

            <div className="space-y-2 rounded-md border bg-muted/30 p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input accent-[hsl(var(--primary))]"
                  checked={editing}
                  disabled={busy}
                  onChange={(event) => {
                    setEditing(event.target.checked);
                    setJsonError(null);
                    if (event.target.checked) setEditedJson(originalJson);
                  }}
                />
                Edit output before approving
              </label>

              {editing ? (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Extracted output (JSON) — the original is preserved in the
                      trace.
                    </span>
                    {dirty ? <StatusBadge tone="warning">edited</StatusBadge> : null}
                  </div>
                  <Textarea
                    aria-label="Edited output JSON"
                    spellCheck={false}
                    className="min-h-[180px] font-mono text-xs"
                    value={editedJson}
                    onChange={(event) => setEditedJson(event.target.value)}
                    disabled={busy}
                  />
                  {jsonError ? (
                    <p role="alert" className="text-xs text-destructive">
                      {jsonError}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>

            {action.isError ? (
              <p role="alert" className="text-sm text-destructive">
                Could not submit decision: {(action.error as Error).message}
              </p>
            ) : null}

            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={() => submit("approve")}
                disabled={busy}
                aria-label={dirty ? "Approve with edited output" : "Approve run"}
              >
                {busy && action.variables?.action === "approve" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                {dirty ? "Approve edited" : "Approve"}
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => submit("reject")}
                disabled={busy}
                aria-label="Reject run"
              >
                {busy && action.variables?.action === "reject" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <X className="h-4 w-4" />
                )}
                Reject
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
