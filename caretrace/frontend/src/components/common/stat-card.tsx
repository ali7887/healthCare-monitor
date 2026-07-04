import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Tone } from "@/components/common/status-badge";

const TONE_TEXT: Record<Tone, string> = {
  success: "text-emerald-600 dark:text-emerald-400",
  warning: "text-amber-600 dark:text-amber-400",
  danger: "text-rose-600 dark:text-rose-400",
  info: "text-sky-600 dark:text-sky-400",
  neutral: "text-foreground",
};

const TONE_ICON_BG: Record<Tone, string> = {
  success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  danger: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  info: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  neutral: "bg-primary/10 text-primary",
};

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  loading = false,
}: {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
  icon: LucideIcon;
  tone?: Tone;
  loading?: boolean;
}) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </CardTitle>
        <span
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            TONE_ICON_BG[tone]
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
      </CardHeader>
      <CardContent className="space-y-1">
        {loading || value === null || value === undefined ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <div className={cn("text-2xl font-semibold tabular-nums", TONE_TEXT[tone])}>
            {value}
          </div>
        )}
        {hint ? (
          loading ? (
            <Skeleton className="h-3 w-24" />
          ) : (
            <p className="text-xs text-muted-foreground">{hint}</p>
          )
        ) : null}
      </CardContent>
    </Card>
  );
}
