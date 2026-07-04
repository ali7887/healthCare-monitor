import { AlertOctagon, Inbox, RotateCw, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/status-badge";

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon className="h-5 w-5" />
      </span>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  statusLabel = "API unreachable",
  onRetry,
}: {
  title?: string;
  description?: string;
  statusLabel?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400">
        <AlertOctagon className="h-5 w-5" />
      </span>
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <StatusBadge tone="danger">{statusLabel}</StatusBadge>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="h-4 w-4" />
          Retry
        </Button>
      ) : null}
    </div>
  );
}
