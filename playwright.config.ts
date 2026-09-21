import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
// Workers and fixture seeding share one disposable database.
const data = process.env.RESEARCHOS_E2E_DIR || mkdtempSync(join(tmpdir(), "researchos-e2e-"));
process.env.RESEARCHOS_E2E_DIR = data;
process.env.DATABASE_URL = "sqlite:///" + join(data, "test.db");
process.env.DATA_DIR = data;
process.env.LLM_API_KEY = "";
process.env.EMBEDDING_API_KEY = "";
process.env.ALLOWED_ORIGINS = "http://127.0.0.1:8766";
process.env.COOKIE_SECURE = "false";
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 45000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8766",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  reporter: "list",
  globalTeardown: "./tests/e2e/teardown.ts",
  webServer: {
    command: (process.platform === "win32" ? '".venv\\Scripts\\python.exe"' : "python") + " -m tests.serve_e2e",
    url: "http://127.0.0.1:8766/api/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
