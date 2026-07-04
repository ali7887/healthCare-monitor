import { expect, test } from "@playwright/test";

import {
  firstPendingReview,
  getRunJson,
  openDashboard,
  pendingReviewCount,
  runStatus,
} from "../helpers";

/**
 * The primary demo path: a reviewer opens a flagged run, corrects the extracted
 * output, and approves it. This is the flow shown in the demo runbook, so it is
 * the one we protect with browser automation.
 *
 * Note on assertions: approving invalidates the run-detail query, so the page
 * refetches and the review panel (rendered only while status is "needs_review")
 * unmounts. We therefore assert the *durable* outcome — the run now reads
 * "Reviewed", the panel is gone, and the API confirms the persisted edit — not
 * the transient success banner.
 */
test("reviewer edits and approves a flagged run, and the decision persists", async ({
  page,
  request,
}) => {
  // Arrange: the dashboard renders its operational surfaces from seeded data.
  await openDashboard(page);
  const countBefore = await pendingReviewCount(request);
  expect(countBefore).toBeGreaterThan(0);

  // Locate a pending review via the API, then drive the UI to act on its run.
  const review = await firstPendingReview(request);
  await page.goto(`/dashboard/runs/${review.run_id}`);

  // The trace viewer shows the run and its human-review panel.
  await expect(page.getByText("Extracted clinical fields")).toBeVisible();
  await expect(page.getByTestId("review-actions")).toBeVisible();

  // Edit the structured output: turn on the editor and supply a corrected note.
  await page.getByLabel("Edit output before approving").check();
  const editor = page.getByLabel("Edited output JSON");
  await expect(editor).toBeVisible();
  const editedSummary = "Reviewed and corrected during E2E verification.";
  await editor.fill(
    JSON.stringify(
      {
        note_summary: editedSummary,
        observations: [{ text: "Values confirmed against the chart." }],
      },
      null,
      2
    )
  );

  // Approve the (edited) output.
  await page.getByRole("button", { name: "Approve with edited output" }).click();

  // Assert the durable outcome: the run refetches as "reviewed" and the review
  // panel is no longer offered.
  await expect(page.getByTestId("review-actions")).toHaveCount(0);
  await expect(page.getByText("Reviewed", { exact: true }).first()).toBeVisible();

  // The decision persisted, the edit was stored as the final output, and the
  // item left the pending queue.
  await expect.poll(() => runStatus(request, review.run_id)).toBe("reviewed");
  const persisted = await getRunJson(request, review.run_id);
  expect((persisted.final_output as { note_summary?: string }).note_summary).toBe(editedSummary);
  expect(await pendingReviewCount(request)).toBe(countBefore - 1);

  // The dashboard still renders meaningfully after the mutation.
  await openDashboard(page);
});
