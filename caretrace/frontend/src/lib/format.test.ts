import { describe, expect, it } from "vitest";

import {
  formatConfidence,
  formatDateTime,
  formatProvider,
} from "@/lib/format";

describe("formatDateTime", () => {
  it("renders day-first, 24-hour, pinned to UTC with an explicit label", () => {
    // 14:32 UTC must render as 14:32 UTC regardless of the machine's zone.
    expect(formatDateTime("2026-07-06T14:32:00Z")).toBe("06 Jul 2026, 14:32 UTC");
  });

  it("renders a dash for missing values", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
  });
});

describe("formatProvider", () => {
  it("uses brand casing for known providers", () => {
    expect(formatProvider("openai")).toBe("OpenAI");
    expect(formatProvider("ollama")).toBe("Ollama");
  });

  it("capitalizes unknown providers and dashes missing ones", () => {
    expect(formatProvider("acme")).toBe("Acme");
    expect(formatProvider(null)).toBe("—");
  });
});

describe("formatConfidence", () => {
  it("renders a percentage or a dash", () => {
    expect(formatConfidence(0.93)).toBe("93%");
    expect(formatConfidence(null)).toBe("—");
  });
});
