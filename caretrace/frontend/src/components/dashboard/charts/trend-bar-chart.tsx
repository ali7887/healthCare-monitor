"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ROUTING_SERIES } from "@/components/dashboard/charts/routing-series";
import type { TimeseriesPoint } from "@/lib/api/types";

const AXIS_COLOR = "#94a3b8"; // slate-400 — legible in light and dark
const GRID_COLOR = "rgba(148, 163, 184, 0.18)";

function formatBucket(iso: string): string {
  // Day-first short date ("6 Jul") for European readers.
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

function TrendTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean;
  label?: string;
  payload?: Array<{ dataKey?: string; value?: number }>;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border bg-card px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-medium text-foreground">{label}</div>
      {ROUTING_SERIES.map((series) => {
        const entry = payload.find((p) => p.dataKey === series.key);
        return (
          <div key={series.key} className="flex items-center gap-2 tabular-nums">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: series.color }}
            />
            <span className="text-muted-foreground">{series.label}</span>
            <span className="ml-auto font-medium text-foreground">
              {entry?.value ?? 0}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Presentational stacked-bar trend. Callers supply the time-series points.
 * Bars, not interpolated areas: the series is discrete daily counts, so a
 * smooth curve would suggest values between days that never existed, and the
 * translucent stacked-area fills blended muddily on dark surfaces. Solid bar
 * fills render identically in both themes.
 */
export function TrendBarChart({ points }: { points: TimeseriesPoint[] }) {
  const data = points.map((point) => ({ ...point, label: formatBucket(point.bucket) }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={GRID_COLOR} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: AXIS_COLOR }}
            tickLine={false}
            axisLine={false}
            minTickGap={16}
          />
          <YAxis
            allowDecimals={false}
            width={32}
            tick={{ fontSize: 11, fill: AXIS_COLOR }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<TrendTooltip />} cursor={{ fill: GRID_COLOR }} />
          {ROUTING_SERIES.map((series) => (
            <Bar
              key={series.key}
              dataKey={series.key}
              name={series.label}
              stackId="runs"
              fill={series.color}
              maxBarSize={28}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
