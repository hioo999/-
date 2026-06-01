import { defineConfig, devices } from '@playwright/test';

const smokePort = Number(process.env.AGENT_CONSOLE_SMOKE_PORT || 3100);
const smokeBaseUrl = `http://127.0.0.1:${smokePort}`;

export default defineConfig({
  testDir: './tests/browser',
  outputDir: './node_modules/.cache/playwright-results',
  timeout: 30_000,
  use: {
    baseURL: smokeBaseUrl,
    trace: 'retain-on-failure'
  },
  webServer: {
    command: `npm run dev -- --port ${smokePort} --strictPort`,
    url: smokeBaseUrl,
    reuseExistingServer: false,
    timeout: 60_000
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
