import { defineConfig } from '@playwright/test'

// Runs against a running app (CI: the Docker image on port 8000). Locally it uses the installed Chrome.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.E2E_URL || 'http://localhost:8000',
    channel: process.env.CI ? undefined : 'chrome',
  },
})
