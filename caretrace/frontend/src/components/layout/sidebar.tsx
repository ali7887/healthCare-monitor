"use client";

import { Activity, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/components/layout/nav";
import { cn } from "@/lib/utils";

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2.5 border-b px-6">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <ShieldCheck className="h-5 w-5" />
        </span>
        <span className="text-[15px] font-semibold tracking-tight">
          healthCare<span className="text-primary">-monitor</span>
        </span>
      </div>

      <div className="px-4 pb-2 pt-4">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Operations
        </p>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4",
                  active
                    ? "text-primary"
                    : "text-muted-foreground group-hover:text-accent-foreground"
                )}
              />
              {item.title}
            </Link>
          );
        })}
      </nav>

      <div className="m-3 rounded-lg border bg-muted/40 p-3">
        <div className="flex items-center gap-2 text-xs font-medium text-foreground">
          <Activity className="h-4 w-4 text-primary" />
          Deterministic pipeline
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
          Validation, traceability, and human review for AI-assisted
          documentation.
        </p>
      </div>
    </aside>
  );
}
