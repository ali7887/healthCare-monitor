"use client";

import { AlertOctagon, RotateCw } from "lucide-react";
import { Component, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { recordEvent } from "@/lib/telemetry";

interface Props {
  children: ReactNode;
  /** Optional label so the fallback names the area that failed. */
  section?: string;
}

interface State {
  error: Error | null;
}

/**
 * Lightweight client error boundary for a dashboard region. Catches render-time
 * exceptions that React Query's error states can't (e.g. a bad shape slipping
 * past types) so one broken widget never blanks the whole app. No new deps —
 * plain React class boundary. `reset` clears the caught error to re-attempt a
 * render after the user retries.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error): void {
    // Surface widget-level failures to local telemetry so the dev observability
    // panel shows which region broke (safe metadata only — no payloads).
    recordEvent("widget_error", {
      status: "failure",
      meta: { section: this.props.section ?? "unknown", error: error.message },
    });
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const isDev = process.env.NODE_ENV !== "production";
    const label = this.props.section ?? "this section";

    return (
      <Card>
        <div
          role="alert"
          className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400">
            <AlertOctagon className="h-5 w-5" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              Something went wrong loading {label}.
            </p>
            <p className="mx-auto max-w-sm text-sm text-muted-foreground">
              The rest of the dashboard is still available. Try reloading this
              section.
            </p>
          </div>
          {isDev ? (
            <pre className="max-w-full overflow-x-auto rounded bg-muted px-3 py-2 text-left text-xs text-muted-foreground">
              {error.message}
            </pre>
          ) : null}
          <Button variant="outline" size="sm" onClick={this.reset}>
            <RotateCw className="h-4 w-4" />
            Try again
          </Button>
        </div>
      </Card>
    );
  }
}
