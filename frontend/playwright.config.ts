import { defineConfig, devices } from '@playwright/test'

const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 5176)
const backendPort = Number(process.env.PLAYWRIGHT_BACKEND_PORT || 8123)
const apiBaseURL = process.env.VITE_API_BASE_URL || `http://127.0.0.1:${backendPort}`

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: `../backend/venv/bin/python -m uvicorn main:app --app-dir ../backend --host 127.0.0.1 --port ${backendPort}`,
      url: `${apiBaseURL}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `VITE_API_BASE_URL=${apiBaseURL} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
})
