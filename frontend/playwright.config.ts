import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const frontendPort = Number(process.env.PLAYWRIGHT_FRONTEND_PORT || 5176)
const backendPort = Number(process.env.PLAYWRIGHT_BACKEND_PORT || 8123)
const apiBaseURL = process.env.VITE_API_BASE_URL || `http://127.0.0.1:${backendPort}`
const backendPython = process.env.PLAYWRIGHT_BACKEND_PYTHON || (existsSync('../backend/venv/bin/python') ? '../backend/venv/bin/python' : 'python3')
const backendCorsOrigins = process.env.BACKEND_CORS_ORIGINS || [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
  'http://127.0.0.1:5173',
  'http://localhost:5173',
].join(',')
const databaseURL = process.env.PLAYWRIGHT_DATABASE_URL || `sqlite:///${join(tmpdir(), `ip_system_e2e_${backendPort}.db`)}`
const quote = (value: string) => JSON.stringify(value)

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
      command: `DATABASE_URL=${quote(databaseURL)} ADMIN_PASSWORD=${quote(process.env.ADMIN_PASSWORD || 'secret123')} BACKEND_CORS_ORIGINS=${quote(backendCorsOrigins)} ${quote(backendPython)} -m uvicorn main:app --app-dir ../backend --host 127.0.0.1 --port ${backendPort}`,
      url: `${apiBaseURL}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `VITE_API_BASE_URL=${apiBaseURL} npx vite --host 127.0.0.1 --port ${frontendPort} --strictPort`,
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
