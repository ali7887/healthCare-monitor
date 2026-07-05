import { expect, test } from "@playwright/test";

import { firstRunWithStatus, openDashboard, pendingReviews } from "../helpers";

/**
 * Portfolio ("production") screenshot set. Same deterministic, honest strategy
 * as the demo capture pipeline (`../screenshots/capture.spec.ts`), but produces
 * the curated set referenced by `docs/PRODUCT_OVERVIEW.md`, written to
 * `docs/screenshots/production/`. Includes the AI reviewer assistant panel.
 *
 * Run with `npm run e2e:screens:prod`. Captures run serially against a freshly
 * seeded backend, so the images reflect real application state.
 */

const OUT = "../../docs/screenshots/production"; // repo/docs/screenshots/production

test.describe.configure({ mode: "serial" });

test("dashboard overview", async ({ page }) => {
  await openDashboard(page);
  await page.screenshot({ path: `${OUT}/01-dashboard-overview.png`, fullPage: true });
});

test("run detail / reasoning panel", async ({ page, request }) => {
  const run = await firstRunWithStatus(request, "reviewed");
  await page.goto(`/dashboard/runs/${run.id}`);
  await expect(page.getByTestId("reasoning-panel")).toBeVisible();
  await expect(page.getByTestId("confidence-meter")).toBeVisible();
  await expect(page.getByText("Extracted clinical fields")).toBeVisible();
  await page.screenshot({ path: `${OUT}/02-run-detail-trace.png`, fullPage: true });
});

test("ai reviewer assistant panel", async ({ page, request }) => {
  // Advisory analysis on a still-pending run. This never mutates the run, so it
  // leaves the pending review intact for the later capture steps.
  const [review] = await pendingReviews(request);
  await page.goto(`/dashboard/runs/${review.run_id}`);
  await expect(page.getByTestId("ai-assistant-panel")).toBeVisible();
  await page.getByTestId("assistant-analyze-button").click();
  await expect(page.getByTestId("assistant-result")).toBeVisible({ timeout: 15_000 });
  await page.screenshot({ path: `${OUT}/05-assistant-panel.png`, fullPage: true });
});

test("review edit state", async ({ page, request }) => {
  const [review] = await pendingReviews(request);
  await page.goto(`/dashboard/runs/${review.run_id}`);
  await page.getByLabel("Edit output before approving").check();
  const editor = page.getByLabel("Edited output JSON");
  await expect(editor).toBeVisible();
  await editor.fill(
    JSON.stringify(
      {
        note_summary: "Dose verified against the medication chart; corrected to 5mg.",
        medications: [{ name: "Amlodipine", dose: "5mg", route: "oral" }],
      },
      null,
      2
    )
  );
  // Do NOT approve — capture the editor state only (no mutation).
  await page.screenshot({ path: `${OUT}/03-review-edit-state.png`, fullPage: true });
});

test("post-approval state", async ({ page, request }) => {
  const items = await pendingReviews(request);
  const review = items[items.length - 1];
  await page.goto(`/dashboard/runs/${review.run_id}`);
  await page.getByRole("button", { name: "Approve run" }).click();
  await expect(page.getByTestId("review-actions")).toHaveCount(0);
  await expect(page.getByText("Reviewed", { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/04-post-approval.png`, fullPage: true });
});
