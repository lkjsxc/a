import { defineConfig, devices } from '@playwright/test';
const remote = process.env.BASE_URL;
export default defineConfig({
  testDir: './site/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : 3,
  timeout: 45000,
  expect: { timeout: 8000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: remote || 'http://127.0.0.1:4173/a/', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile-webkit', use: { ...devices['iPhone 13'], defaultBrowserType: 'webkit' } },
  ],
  webServer: remote ? undefined : { command: 'npm run preview', url: 'http://127.0.0.1:4173/a/', reuseExistingServer: !process.env.CI, timeout: 20000 },
});
