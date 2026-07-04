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
