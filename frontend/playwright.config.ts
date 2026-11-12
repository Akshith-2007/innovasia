import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const apiPort = process.env.API_PORT ?? "8000";
const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../backend");
const venvPython =
  process.platform === "win32" ? path.join(backend, ".venv/Scripts/python.exe") : path.join(backend, ".venv/bin/python");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: true,
  retries: 1, // reported as "flaky" when used; guards against attaching to a server still shutting down
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "tablet", use: { ...devices["Desktop Chrome"], viewport: { width: 820, height: 1180 }, hasTouch: true } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  // Real backend + real dev server. Reuses ./dev.sh servers if they are already running.
  webServer: [
    {
      command: `"${venvPython}" -m uvicorn app.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: backend,
      // Many parallel page loads from one IP; the limiter itself is covered by backend unit tests.
      env: { RATE_LIMIT_PER_MINUTE: "0" },
      url: `http://127.0.0.1:${apiPort}/api/v1/health`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      env: { VITE_API_BASE_URL: `http://127.0.0.1:${apiPort}/api/v1` },
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
