import { expect, test } from "@playwright/test";

import {
  firstPendingReview,
  firstRunWithStatus,
  pendingReviewCount,
  runStatus,
} from "../helpers";

/**
 * Secondary, high-value coverage around the review workflow. Kept small and
 * honest — each test asserts a real, durable UI state (approving/rejecting
 * refetches the run, so the review panel unmounts and the status badge updates).
 */

test("reviewer rejects a flagged run and the rejection persists", async ({ page, request }) => {
  const countBefore = await pendingReviewCount(request);
  const review = await firstPendingReview(request);

  await page.goto(`/dashboard/runs/${review.run_id}`);
  await expect(page.getByTestId("review-actions")).toBeVisible();

  await page.getByRole("button", { name: "Reject run" }).click();

  // Durable outcome: the panel is withdrawn and the run reads "Rejected".
  await expect(page.getByTestId("review-actions")).toHaveCount(0);
  await expect(page.getByText("Rejected", { exact: true }).first()).toBeVisible();

  await expect.poll(() => runStatus(request, review.run_id)).toBe("rejected");
  expect(await pendingReviewCount(request)).toBe(countBefore - 1);
});

test("an already-decided run shows its outcome and offers no review actions", async ({
  page,
  request,
}) => {
  // Seeded "reviewed" runs are terminal: the UI must not offer approve/reject.
  // This is the reachable UI face of the backend's immutable-decision guard —
  // the operator can never re-decide a run that is already resolved.
  const reviewed = await firstRunWithStatus(request, "reviewed");

  await page.goto(`/dashboard/runs/${reviewed.id}`);

  // The status badge appears in both the header and the metadata panel.
  await expect(page.getByText("Reviewed", { exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("review-actions")).toHaveCount(0);
  // The audit trail is still fully visible for a decided run. (Card titles are
  // styled divs, not headings, so we match on their text.)
  await expect(page.getByText("Confidence breakdown")).toBeVisible();
  await expect(page.getByText("Validation checks")).toBeVisible();
});
