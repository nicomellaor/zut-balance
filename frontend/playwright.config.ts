import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'on-first-retry' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }, { name: 'mobile', use: { ...devices['Pixel 5'] } }],
  webServer: [
    {
      command: 'ZUT_BALANCE_DATABASE_PATH=/tmp/zut-balance-e2e.sqlite3 ZUT_BALANCE_API_KEY=test-api-key ZUT_BALANCE_CORS_ORIGINS=http://127.0.0.1:5173 PYTHONPATH=src /tmp/opencode/zut-balance-venv/bin/python -m uvicorn zut_balance.api:app --host 127.0.0.1 --port 8000',
      cwd: '..',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
    },
    {
      command: 'VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
    },
  ],
})
