/** Presentation helpers shared across dashboard surfaces. */

export function formatConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`;
}

export function formatCost(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${value.toFixed(4)}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  // Day-first, 24-hour, with an explicit timezone label (e.g. "06 Jul 2026,
  // 14:32 CEST") — unambiguous for European readers and auditable in demos.
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

// Brand casing can't be derived from the enum value ("openai" → "OpenAI"), so
// known providers are mapped explicitly; unknown ones fall back to capitalized.
const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  ollama: "Ollama",
};

export function formatProvider(provider: string | null | undefined): string {
  if (!provider) return "—";
  return (
    PROVIDER_LABELS[provider.toLowerCase()] ??
    provider.charAt(0).toUpperCase() + provider.slice(1)
  );
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function percent(part: number, total: number): number {
  return total === 0 ? 0 : Math.round((part / total) * 100);
}
