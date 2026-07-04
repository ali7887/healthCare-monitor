export interface LegendItem {
  label: string;
  value: number;
  percent: number;
  color: string;
}

/** Legend / summary list for a chart. Purely presentational. */
export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-3 text-sm">
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-muted-foreground">{item.label}</span>
          <span className="ml-auto tabular-nums font-medium text-foreground">
            {item.value}
          </span>
          <span className="w-10 text-right tabular-nums text-xs text-muted-foreground">
            {item.percent}%
          </span>
        </li>
      ))}
    </ul>
  );
}
