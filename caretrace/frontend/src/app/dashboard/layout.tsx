import { ApiStatus } from "@/components/layout/api-status";
import { MobileNav } from "@/components/layout/mobile-nav";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-muted/30">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-3 border-b bg-card/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-card/60 sm:px-6">
          <MobileNav />
          <span className="text-sm font-medium text-muted-foreground md:hidden">
            healthCare-monitor
          </span>
          <div className="ml-auto flex items-center gap-2">
            <ApiStatus />
            <ThemeToggle />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
