import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithClient } from "@/test/utils";
import type { SearchResponse } from "@/lib/api/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const useSearch = vi.fn();
vi.mock("@/lib/hooks/use-search", () => ({
  useSearch: (query: string) => useSearch(query),
}));

import { CommandPalette } from "@/components/search/command-palette";

const RESULTS: SearchResponse = {
  query: "amlodipine",
  results: [
    {
      run_id: "run-abc-123",
      status: "needs_review",
      routing_decision: "human_review",
      confidence: 0.66,
      snippet: "…Amlodipine given, dose unclear…",
      created_at: "2026-07-06T10:00:00Z",
      pending_review: true,
    },
  ],
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("CommandPalette", () => {
  it("opens on Ctrl+K and closes on Escape", async () => {
    useSearch.mockReturnValue({ data: undefined, isFetching: false });
    renderWithClient(<CommandPalette />);

    expect(screen.queryByTestId("command-palette")).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(await screen.findByTestId("command-palette")).toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() =>
      expect(screen.queryByTestId("command-palette")).not.toBeInTheDocument()
    );
  });

  it("renders run results and navigates to the run on click", async () => {
    useSearch.mockReturnValue({ data: RESULTS, isFetching: false });
    renderWithClient(<CommandPalette />);

    await userEvent.click(screen.getByRole("button", { name: /search/i }));

    const result = await screen.findByText(/amlodipine given, dose unclear/i);
    await userEvent.click(result);

    expect(push).toHaveBeenCalledWith("/dashboard/runs/run-abc-123");
  });

  it("groups pending runs under the review queue heading", async () => {
    useSearch.mockReturnValue({ data: RESULTS, isFetching: false });
    renderWithClient(<CommandPalette />);

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(await screen.findByText(/review queue/i)).toBeInTheDocument();
  });
});
