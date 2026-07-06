import { Activity, LayoutDashboard, Search, type LucideIcon } from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { title: "Dashboard Overview", href: "/dashboard", icon: LayoutDashboard },
  { title: "Monitoring", href: "/dashboard/runs", icon: Activity },
  { title: "Trace Viewer", href: "/dashboard/trace", icon: Search },
];

/**
 * Shared active-state rule for the sidebar and mobile drawer. A run detail
 * page (/dashboard/runs/<id>) *renders* the Trace Viewer, so it highlights
 * Trace Viewer — Monitoring stays active only on the runs list itself.
 */
export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard";
  if (href === "/dashboard/runs") return pathname === "/dashboard/runs";
  if (href === "/dashboard/trace") {
    return (
      pathname === href ||
      pathname.startsWith(`${href}/`) ||
      /^\/dashboard\/runs\/[^/]+/.test(pathname)
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
