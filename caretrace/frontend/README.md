# healthCare-monitor — Frontend

Next.js 15 (App Router) dashboard for the healthCare-monitor backend.

## Stack
- Next.js 15 + React 19 + TypeScript
- Tailwind CSS + shadcn-style UI primitives
- TanStack Query (server-state caching)
- Lucide icons; Recharts (reserved for the charts step)

## Setup
```bash
cd caretrace/frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev        # http://localhost:3000  ->  redirects to /dashboard
```

The backend must be running (default `http://localhost:8000/api`).

## Structure
```
src/
  app/
    layout.tsx            # root layout + global providers
    page.tsx              # redirects to /dashboard
    dashboard/
      layout.tsx          # shell: sidebar + top bar + scrolling main
      page.tsx            # Overview (stat cards)
      runs/page.tsx       # Monitoring (runs table)
      trace/page.tsx      # Trace Viewer (placeholder)
  components/
    providers.tsx         # QueryClientProvider + ThemeProvider
    theme-provider.tsx    # next-themes wrapper
    theme-toggle.tsx
    layout/{sidebar,nav}  # navigation
    dashboard/            # stat-cards, runs-table (data flow)
    ui/                   # button, card, badge, skeleton
  lib/
    api/{client,types,dashboard,runs}.ts   # typed API client
    hooks/{use-dashboard-stats,use-runs}.ts
```

## Phase 12 scope
- Step 1: layout, sidebar, providers, theme, page shells.
- Step 2: typed API client + React Query hooks wired to `GET /api/dashboard/stats`
  and `GET /api/runs` (stat cards + monitoring table).

Charts (Recharts) and the deep trace viewer come in the next step.
