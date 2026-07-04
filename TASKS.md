TASKS.md — Project Roadmap & Task Board

Legend





Completed



[/] In Progress



Pending



🏁 Phase 10: Persistence & API Integration





Resolve database circular imports by separating Base configuration to app/db/base.py.



Implement the persistence.py service layer to handle database transactions and rollbacks.



Expose POST /api/process pipeline routing endpoint.



Expose review queue endpoints: GET /api/reviews and POST /api/reviews/{id}/action.



Write comprehensive integration tests for persistence and API routes (72 tests passing).

📊 Phase 11: Read-Heavy APIs





Design dashboard aggregation schemas DashboardStatsResponse and pagination metadata wrappers.



Write optimized read queries (get_runs and get_dashboard_stats) using SQLAlchemy native aggregations (func.count, func.avg).



Implement query-param filters (Confidence score, status, routing decision, paging offset/limit).



Verify API performance metrics and ensure zero regressions across all 72 backend tests.

🚀 Phase 12: Frontend MVP (Next.js Dashboard)

Target Directory: caretrace/frontend/

12.1 — Base UI Components & Layout





[x] Set up Next.js 15 project structure (App Router) in caretrace/frontend/ (build passes)



[x] Configure Tailwind CSS, global typography, and design variables



[x] Initialize Shadcn UI components library (button, card, badge, skeleton primitives + tokens)



[x] Implement Global Layout Wrapper (app/layout.tsx) including TanStack Query providers



[x] Implement Main Dashboard Layout Shell (app/dashboard/layout.tsx)



[x] Implement Sidebar component (components/layout/sidebar.tsx) with active state tracking



[x] Verify local layout routing without visual artifacts (next build: 7 routes compiled, types valid)

12.2 — API Integration & Data Flow





[x] Implement API client configuration and fetch wrapper (lib/api/client.ts)



[x] Implement typescript definitions matching Phase 11 Pydantic models



[x] Add TanStack Query hook for GET /api/dashboard/stats



[x] Add TanStack Query hook for GET /api/runs (paginated query)



[x] Bind dashboard cards directly to the stats endpoint (Total, Accepted, Routed, Rejected, Avg Confidence)



[x] Bind dynamic run list table to backend runs query with loading, empty, and error states

12.3 — Interactive Features & Trace View





Integrate TanStack Table for sorting, filtering, and paging controls



Bind table filter states directly to URL query parameters



Add interactive Recharts charts visualizing average confidence levels



Implement Trace Detail view to display raw input payloads, parsed outputs, and structured confidence breakdowns