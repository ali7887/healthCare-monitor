import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithClient } from "@/test/utils";
import type { ReviewActionResponse, RunDetail } from "@/lib/api/types";

// Mock the network edge only; the mutation, its states, and cache invalidation
// all run for real through React Query.
const postReviewAction = vi.fn();
vi.mock("@/lib/api/reviews", () => ({
  postReviewAction: (...args: unknown[]) => postReviewAction(...args),
}));

import { ReviewActions } from "@/components/runs/review-actions";

function makeRun(over: Partial<RunDetail> = {}): RunDetail {
  return {
    id: "run-1",
    provider: "openai",
    status: "needs_review",
    transcript: "t",
    parsed_output: { a: 1 },
    final_output: null,
    confidence_score: 0.7,
    confidence_breakdown: null,
    routing_decision: "human_review",
    routing_reason: "low confidence",
    retry_count: 0,
    warnings_count: 0,
    latency_ms: 10,
    cost: 0.0002,
    raw_model_response: "{}",
    issues: [],
    created_at: "2026-07-01T00:00:00Z",
    pending_review_id: "rev-1",
    ...over,
  };
}

const OK_RESPONSE: ReviewActionResponse = {
  id: "rev-1",
  run_id: "run-1",
  status: "approved",
  run_status: "reviewed",
};

beforeEach(() => {
  postReviewAction.mockReset();
  postReviewAction.mockResolvedValue(OK_RESPONSE);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("ReviewActions", () => {
  it("shows a no-op message and no action buttons without a pending review id", () => {
    renderWithClient(<ReviewActions run={makeRun({ pending_review_id: null })} />);
    expect(
      screen.getByText(/no pending review item is associated/i)
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("approves without edits, sending null notes and no edited output", async () => {
    renderWithClient(<ReviewActions run={makeRun()} />);
    await userEvent.click(screen.getByRole("button", { name: /approve run/i }));

    await waitFor(() =>
      expect(postReviewAction).toHaveBeenCalledWith("rev-1", {
        action: "approve",
        reviewer_notes: null,
        edited_output: null,
      })
    );
    expect(await screen.findByText(/decision recorded/i)).toBeInTheDocument();
  });

  it("rejects with trimmed reviewer notes", async () => {
    postReviewAction.mockResolvedValue({ ...OK_RESPONSE, status: "rejected", run_status: "rejected" });
    renderWithClient(<ReviewActions run={makeRun()} />);

    await userEvent.type(screen.getByLabelText(/reviewer notes/i), "  looks off  ");
    await userEvent.click(screen.getByRole("button", { name: /reject run/i }));

    await waitFor(() =>
      expect(postReviewAction).toHaveBeenCalledWith("rev-1", {
        action: "reject",
        reviewer_notes: "looks off",
        edited_output: null,
      })
    );
  });

  it("blocks approval on invalid JSON and surfaces an alert, without calling the API", async () => {
    renderWithClient(<ReviewActions run={makeRun()} />);
    await userEvent.click(screen.getByLabelText(/edit output before approving/i));

    fireEvent.change(screen.getByLabelText(/edited output json/i), {
      target: { value: "{ not valid json" },
    });
    await userEvent.click(screen.getByRole("button", { name: /approve/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid json/i);
    expect(postReviewAction).not.toHaveBeenCalled();
  });

  it("rejects a non-object edited payload (array) as invalid", async () => {
    renderWithClient(<ReviewActions run={makeRun()} />);
    await userEvent.click(screen.getByLabelText(/edit output before approving/i));

    fireEvent.change(screen.getByLabelText(/edited output json/i), {
      target: { value: "[1, 2, 3]" },
    });
    await userEvent.click(screen.getByRole("button", { name: /approve/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/must be a json object/i);
    expect(postReviewAction).not.toHaveBeenCalled();
  });

  it("approves with a valid edited payload, forwarding the corrected object", async () => {
    renderWithClient(<ReviewActions run={makeRun()} />);
    await userEvent.click(screen.getByLabelText(/edit output before approving/i));

    fireEvent.change(screen.getByLabelText(/edited output json/i), {
      target: { value: '{ "a": 2 }' },
    });
    await userEvent.click(screen.getByRole("button", { name: /approve with edited output/i }));

    await waitFor(() =>
      expect(postReviewAction).toHaveBeenCalledWith("rev-1", {
        action: "approve",
        reviewer_notes: null,
        edited_output: { a: 2 },
      })
    );
  });

  it("surfaces an error alert when the API call fails", async () => {
    postReviewAction.mockRejectedValue(new Error("Review item is already approved"));
    renderWithClient(<ReviewActions run={makeRun()} />);

    await userEvent.click(screen.getByRole("button", { name: /approve run/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not submit decision/i);
    expect(alert).toHaveTextContent(/already approved/i);
  });

  it("disables both buttons while a decision is in flight", async () => {
    let resolve!: (v: ReviewActionResponse) => void;
    postReviewAction.mockReturnValue(new Promise((r) => (resolve = r)));
    renderWithClient(<ReviewActions run={makeRun()} />);

    await userEvent.click(screen.getByRole("button", { name: /approve run/i }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled()
    );
    expect(screen.getByRole("button", { name: /reject/i })).toBeDisabled();

    resolve(OK_RESPONSE);
    expect(await screen.findByText(/decision recorded/i)).toBeInTheDocument();
  });
});
