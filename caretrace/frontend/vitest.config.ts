import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Component tests run under jsdom. The `@` alias mirrors tsconfig so imports
// resolve identically in tests and in the Next build.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": resolve(__dirname, "./src") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
