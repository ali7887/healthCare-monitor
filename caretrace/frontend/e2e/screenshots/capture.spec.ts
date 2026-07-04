import { expect, test } from "@playwright/test";

import { firstRunWithStatus, openDashboard, pendingReviews } from "../helpers";

/**
 * Screenshot capture pipeline. These "tests" exist to produce deterministic,
 * honest UI captures from the seeded dataset — not to assert behavior (the
 * `e2e` project does that). Run with `npm run e2e:screens`; outputs land in
 * `docs/screenshots/`.
 *
 * Captures run serially against a freshly seeded backend, so the images reflect
 * real application state, never a fabricated one.
 */

const OUT = "../../docs/screenshots"; // relative to the frontend cwd → repo/docs/screenshots

test.describe.configure({ mode: "serial" });

test("dashboard overview", async ({ page }) => {
  await openDashboard(page);
  await page.screenshot({ path: `${OUT}/01-dashboard-overview.png`, fullPage: true });
});

test("run detail / trace viewer", async ({ page, request }) => {
  const run = await firstRunWithStatus(request, "auto_saved");
  await page.goto(`/dashboard/runs/${run.id}`);
  // Card titles are styled divs, not headings — match on their text.
  await expect(page.getByText("Extracted clinical fields")).toBeVisible();
  await expect(page.getByText("Confidence breakdown")).toBeVisible();
  await page.screenshot({ path: `${OUT}/02-run-detail-trace.png`, fullPage: true });
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
  // Use a still-pending review (the edit-state capture did not mutate anything).
  const review = items[items.length - 1];
  await page.goto(`/dashboard/runs/${review.run_id}`);
  await page.getByRole("button", { name: "Approve run" }).click();
  // Approving refetches the run: the panel withdraws and the run reads
  // "Reviewed". Capture that durable post-decision state.
  await expect(page.getByTestId("review-actions")).toHaveCount(0);
  await expect(page.getByText("Reviewed", { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/04-post-approval.png`, fullPage: true });
});
