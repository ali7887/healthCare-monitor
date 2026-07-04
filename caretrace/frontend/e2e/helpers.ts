import { type APIRequestContext, type Page, expect } from "@playwright/test";

/**
 * Test helpers. Strategy: use the API to *locate* entities and to *verify*
 * persisted state, and drive the UI only for the flow under test. This keeps
 * the tests deterministic (no brittle table-walking to find a specific run) and
 * makes each test's intent obvious.
 */

export const API_BASE = "http://localhost:8000/api";

export interface ReviewItem {
  id: string;
  run_id: string;
  status: "pending" | "approved" | "rejected";
}

/** Return all pending review items (newest first). */
export async function pendingReviews(request: APIRequestContext): Promise<ReviewItem[]> {
  const res = await request.get(`${API_BASE}/reviews`);
  expect(res.ok(), "GET /reviews should succeed").toBeTruthy();
  return (await res.json()).items as ReviewItem[];
}

/** Grab one pending review to act on, failing loudly if the seed is empty. */
export async function firstPendingReview(request: APIRequestContext): Promise<ReviewItem> {
  const items = await pendingReviews(request);
  expect(items.length, "expected at least one seeded pending review").toBeGreaterThan(0);
  return items[0];
}

export async function pendingReviewCount(request: APIRequestContext): Promise<number> {
  const res = await request.get(`${API_BASE}/reviews`);
  expect(res.ok()).toBeTruthy();
  return (await res.json()).total as number;
}

interface RunSummary {
  id: string;
  status: string;
  routing_decision: string | null;
}

/** Find the first run with a given status (e.g. "reviewed", "auto_saved"). */
export async function firstRunWithStatus(
  request: APIRequestContext,
  status: string
): Promise<RunSummary> {
  const res = await request.get(`${API_BASE}/runs?limit=50`);
  expect(res.ok()).toBeTruthy();
  const items = (await res.json()).items as RunSummary[];
  const match = items.find((r) => r.status === status);
  expect(match, `expected a seeded run with status "${status}"`).toBeTruthy();
  return match as RunSummary;
}

/** Fetch a run's full detail payload from the API (source of truth). */
export async function getRunJson(
  request: APIRequestContext,
  runId: string
): Promise<Record<string, unknown>> {
  const res = await request.get(`${API_BASE}/runs/${runId}`);
  expect(res.ok()).toBeTruthy();
  return (await res.json()) as Record<string, unknown>;
}

/** The run's persisted status (e.g. "reviewed", "rejected"). */
export async function runStatus(request: APIRequestContext, runId: string): Promise<string> {
  return (await getRunJson(request, runId)).status as string;
}

/** Open the dashboard and wait for the three operational surfaces to render. */
export async function openDashboard(page: Page): Promise<void> {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard Overview" })).toBeVisible();
  await expect(page.getByTestId("kpi-strip")).toBeVisible();
  // Charts lazy-load the Recharts chunk and fetch data; give the SVG extra time
  // to mount so a cold production start doesn't cause a flaky miss.
  await expect(
    page.getByTestId("routing-distribution").locator("svg").first()
  ).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByTestId("throughput-trend").locator("svg").first()
  ).toBeVisible({ timeout: 15_000 });
}
