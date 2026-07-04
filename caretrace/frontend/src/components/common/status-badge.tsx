import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Clock,
  ShieldCheck,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { RoutingDecision, RunStatus } from "@/lib/api/types";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  success:
    "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300",
  warning:
    "bg-amber-500/10 text-amber-700 ring-amber-500/25 dark:text-amber-300",
  danger: "bg-rose-500/10 text-rose-700 ring-rose-500/25 dark:text-rose-300",
  info: "bg-sky-500/10 text-sky-700 ring-sky-500/25 dark:text-sky-300",
  neutral:
    "bg-slate-500/10 text-slate-700 ring-slate-500/25 dark:text-slate-300",
};

export function StatusBadge({
  tone,
  icon: Icon,
  children,
  className,
}: {
  tone: Tone;
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE_CLASSES[tone],
        className
      )}
    >
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      {children}
    </span>
  );
}

const ROUTING_META: Record<
  RoutingDecision,
  { tone: Tone; icon: LucideIcon; label: string }
> = {
  auto_save: { tone: "success", icon: CheckCircle2, label: "Auto-save" },
  human_review: { tone: "warning", icon: AlertTriangle, label: "Human review" },
  reject: { tone: "danger", icon: XCircle, label: "Reject" },
};

export function RoutingBadge({
  decision,
}: {
  decision: RoutingDecision | null;
}) {
  if (!decision) {
    return (
      <StatusBadge tone="neutral" icon={CircleDashed}>
        Unrouted
      </StatusBadge>
    );
  }
  const meta = ROUTING_META[decision];
  return (
    <StatusBadge tone={meta.tone} icon={meta.icon}>
      {meta.label}
    </StatusBadge>
  );
}

const STATUS_META: Record<
  RunStatus,
  { tone: Tone; icon: LucideIcon; label: string }
> = {
  auto_saved: { tone: "success", icon: CheckCircle2, label: "Auto-saved" },
  needs_review: { tone: "warning", icon: Clock, label: "Needs review" },
  reviewed: { tone: "info", icon: ShieldCheck, label: "Reviewed" },
  rejected: { tone: "danger", icon: XCircle, label: "Rejected" },
  failed: { tone: "danger", icon: AlertTriangle, label: "Failed" },
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  const meta = STATUS_META[status];
  return (
    <StatusBadge tone={meta.tone} icon={meta.icon}>
      {meta.label}
    </StatusBadge>
  );
}
