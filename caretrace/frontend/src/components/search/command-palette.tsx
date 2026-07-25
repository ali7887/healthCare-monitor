"use client";

import {
  ClipboardCheck,
  FileSearch,
  Loader2,
  Search,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { NAV_ITEMS } from "@/components/layout/nav";
import { RoutingBadge } from "@/components/common/status-badge";
import { useSearch } from "@/lib/hooks/use-search";
import { formatConfidence, formatRelative, shortId } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SearchResult } from "@/lib/api/types";

/** One selectable row in the palette: a page link or a run result. */
interface PaletteItem {
  key: string;
  href: string;
  group: "Pages" | "Review queue" | "Runs";
  render: () => React.ReactNode;
}

/**
 * Global search: a Ctrl+K / Cmd+K command palette over runs, review-queue
 * items, and app pages. Kept deliberately calm and clinical — a labeled
 * search dialog with grouped results, not a generic startup launcher.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global shortcut: Ctrl+K / Cmd+K toggles, Escape closes (handled on the
  // dialog itself so it never swallows Escape elsewhere).
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Reset + focus on open.
  useEffect(() => {
    if (open) {
      setQuery("");
      setDebounced("");
      setActiveIndex(0);
      // Focus after the dialog paints.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Debounce the server query; page filtering stays instant.
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(handle);
  }, [query]);

  const search = useSearch(debounced);

  const items = useMemo<PaletteItem[]>(() => {
    const lowered = query.trim().toLowerCase();
    const pages: PaletteItem[] = NAV_ITEMS.filter(
      (item) => lowered.length === 0 || item.title.toLowerCase().includes(lowered)
    ).map((item) => ({
      key: `page-${item.href}`,
      href: item.href,
      group: "Pages",
      render: () => (
        <span className="flex items-center gap-2.5 text-sm text-foreground">
          <item.icon className="h-4 w-4 text-muted-foreground" />
          {item.title}
        </span>
      ),
    }));

    const runs: PaletteItem[] = (search.data?.results ?? []).map(
      (result: SearchResult) => ({
        key: `run-${result.run_id}`,
        href: `/dashboard/runs/${result.run_id}`,
        group: result.pending_review ? "Review queue" : "Runs",
        render: () => (
          <span className="flex min-w-0 items-center gap-3">
            <span className="font-mono text-xs text-muted-foreground">
              {shortId(result.run_id)}
            </span>
            <RoutingBadge decision={result.routing_decision} />
            <span className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
              {result.snippet}
            </span>
            <span className="hidden shrink-0 tabular-nums text-xs text-muted-foreground sm:block">
              {formatConfidence(result.confidence)} · {formatRelative(result.created_at)}
            </span>
          </span>
        ),
      })
    );

    // Review-queue matches surface first — they are the actionable ones.
    return [
      ...runs.filter((item) => item.group === "Review queue"),
      ...runs.filter((item) => item.group === "Runs"),
      ...pages,
    ];
  }, [query, search.data]);

  // Keep the active row valid as results change.
  useEffect(() => {
    setActiveIndex((current) => Math.min(current, Math.max(items.length - 1, 0)));
  }, [items.length]);

  const navigate = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router]
  );

  const onDialogKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, items.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && items[activeIndex]) {
      event.preventDefault();
      navigate(items[activeIndex].href);
    }
  };

  const showEmpty =
    debounced.trim().length >= 2 &&
    !search.isFetching &&
    (search.data?.results.length ?? 0) === 0;

  let lastGroup: PaletteItem["group"] | null = null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Search (Ctrl+K)"
        className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Search</span>
        <kbd className="hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] sm:inline">
          Ctrl K
        </kbd>
      </button>

      {open ? (
        <div className="fixed inset-0 z-50" data-testid="command-palette">
          <div
            className="absolute inset-0 bg-black/30"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Search runs and pages"
            onKeyDown={onDialogKeyDown}
            className="absolute left-1/2 top-24 w-[min(640px,calc(100vw-2rem))] -translate-x-1/2 overflow-hidden rounded-xl border bg-card shadow-xl"
          >
            <div className="flex items-center gap-2.5 border-b px-4">
              {search.isFetching ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : (
                <Search className="h-4 w-4 text-muted-foreground" />
              )}
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search runs, review queue, transcripts…"
                aria-label="Search query"
                className="h-12 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
            </div>

            <div className="max-h-[50vh] overflow-y-auto p-2">
              {showEmpty ? (
                <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                  <FileSearch className="h-5 w-5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    No runs match “{debounced.trim()}”.
                  </p>
                </div>
              ) : null}

              <ul role="listbox" aria-label="Search results">
                {items.map((item, index) => {
                  const heading = item.group !== lastGroup ? item.group : null;
                  lastGroup = item.group;
                  return (
                    <li key={item.key}>
                      {heading ? (
                        <p className="flex items-center gap-1.5 px-2 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          {heading === "Review queue" ? (
                            <ClipboardCheck className="h-3 w-3" />
                          ) : null}
                          {heading}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        role="option"
                        aria-selected={index === activeIndex}
                        onMouseEnter={() => setActiveIndex(index)}
                        onClick={() => navigate(item.href)}
                        className={cn(
                          "w-full rounded-lg px-2.5 py-2 text-left transition-colors",
                          index === activeIndex
                            ? "bg-primary/10"
                            : "hover:bg-accent/60"
                        )}
                      >
                        {item.render()}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="flex items-center gap-3 border-t bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground">
              <span>
                <kbd className="rounded border bg-card px-1 font-mono">↑↓</kbd> navigate
              </span>
              <span>
                <kbd className="rounded border bg-card px-1 font-mono">Enter</kbd> open
              </span>
              <span>
                <kbd className="rounded border bg-card px-1 font-mono">Esc</kbd> close
              </span>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
