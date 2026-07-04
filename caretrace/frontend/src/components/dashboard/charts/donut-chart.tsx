"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { percent } from "@/lib/format";

export interface ChartSlice {
  label: string;
  value: number;
  color: string;
}

function DonutTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartSlice }>;
  total: number;
}) {
  if (!active || !payload?.length) return null;
  const slice = payload[0].payload;
  return (
    <div className="rounded-md border bg-card px-3 py-2 text-xs shadow-md">
      <div className="flex items-center gap-2 font-medium text-foreground">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: slice.color }}
        />
        {slice.label}
      </div>
      <div className="mt-1 tabular-nums text-muted-foreground">
        {slice.value} runs · {percent(slice.value, total)}%
      </div>
    </div>
  );
}

/** Presentational donut. No data fetching — callers map data to slices. */
export function DonutChart({
  slices,
  total,
  centerLabel = "total runs",
}: {
  slices: ChartSlice[];
  total: number;
  centerLabel?: string;
}) {
  return (
    <div className="relative mx-auto h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={slices}
            dataKey="value"
            nameKey="label"
            innerRadius="62%"
            outerRadius="92%"
            paddingAngle={2}
            strokeWidth={0}
          >
            {slices.map((slice) => (
              <Cell key={slice.label} fill={slice.color} />
            ))}
          </Pie>
          <Tooltip content={<DonutTooltip total={total} />} cursor={false} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tabular-nums">{total}</span>
        <span className="text-xs text-muted-foreground">{centerLabel}</span>
      </div>
    </div>
  );
}
