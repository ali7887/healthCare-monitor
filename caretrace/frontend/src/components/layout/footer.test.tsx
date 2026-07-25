import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Footer } from "@/components/layout/footer";

describe("Footer", () => {
  it("renders the designer branding link securely", () => {
    render(<Footer />);
    const link = screen.getByRole("link", { name: "Ali Kiani" });
    expect(link).toHaveAttribute("href", "https://alikiani.vercel.app");
    expect(link).toHaveAttribute("target", "_blank");
    // Secure external link — must not leak the opener or referrer.
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/designed & built by/i)).toBeInTheDocument();
  });
});
