import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config for healthCare-monitor.
 *
 * Reproducibility model:
 *  - Playwright owns both servers via `webServer` (nothing to start by hand).
 *  - The backend runs on an ISOLATED SQLite file (`caretrace_e2e.db`) and
 *    re-seeds on every start, so E2E has a deterministic dataset and never
 *    touches the developer's demo database (`caretrace_demo.db`).
 *  - The frontend runs a PRODUCTION build (`next build && next start`). This is
 *    intentional: the dev-only debug overlay is tree-shaken out, so the app
 *    (and the captured screenshots) match what a real user sees. The client
 *    defaults its API base URL to http://localhost:8000/api, so no build-time
 *    env is needed to point it at the E2E backend.
 *  - We use the system Chrome (`channel: "chrome"`) so no browser binary needs
 *    to be downloaded.
 *
 * Two projects share the same servers:
 *  - `e2e`         — functional demo-path tests (`npm run test:e2e`)
 *  - `screenshots` — deterministic UI captures      (`npm run e2e:screens`)
 * Each project reseeds via its own server lifecycle, so they never share state.
 */

const BACKEND_DIR = "../backend";
const E2E_DATABASE_URL = "sqlite:///./caretrace_e2e.db";
const FRONTEND_URL = "http://localhost:3000";
const BACKEND_HEALTH = "http://localhost:8000/api/health";

export default defineConfig({
  testDir: "./e2e",
  // Mutating flows consume seeded review items, so run serially and in order.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],

  use: {
    baseURL: FRONTEND_URL,
    channel: "chrome",
    trace: "retain-on-failure",
    // Deterministic viewport for stable screenshots.
    viewport: { width: 1440, height: 900 },
  },

  projects: [
    {
      name: "e2e",
      testDir: "./e2e/tests",
      // Spread the device first, then re-assert channel + a wider viewport so the
      // device preset's 1280x720 doesn't override our deterministic capture size.
      use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } },
    },
    {
      name: "screenshots",
      testDir: "./e2e/screenshots",
      use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } },
    },
  ],

  webServer: [
    {
      // Seed the isolated DB, then serve it. `&&` works on both cmd and bash.
      command:
        "uv run python -m app.seed_demo && uv run uvicorn app.main:app --port 8000",
      cwd: BACKEND_DIR,
      env: { DATABASE_URL: E2E_DATABASE_URL },
      url: BACKEND_HEALTH,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "npm run build && npm run start -- --port 3000",
      url: `${FRONTEND_URL}/dashboard`,
      reuseExistingServer: false,
      timeout: 300_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
