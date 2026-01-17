import { test, expect } from '@playwright/test';

const BACKEND_URL = 'http://127.0.0.1:8765';

test.describe('Flash AI E2E', () => {

  test.beforeEach(async ({ page }) => {
    // Skip onboarding
    await page.addInitScript(() => {
      window.localStorage.setItem('flash_onboarding_complete', 'true');
    });

    // Reset session before each test
    await page.request.post(`${BACKEND_URL}/permission/revoke`);

    // Enable Mock STT for stable testing
    await page.request.put(`${BACKEND_URL}/settings/voice`, {
      data: {
        engine_preference: 'mock',
        mock_stt: true,
        record_seconds: 2, // Quick but enough to catch LISTENING state
        openai_api_key: 'sk-test-mock-key'
      }
    });
  });

  test('A: UI Loads + WebSocket Connects', async ({ page }) => {
    await page.goto('/');
    
    // Check Core Button exists
    await expect(page.getByTestId('core-button')).toBeVisible();
    
    // Check App Status label default
    // Wait for transient noise/startup to clear
    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });
    
    // Check Session Status default
    await expect(page.getByTestId('session-status')).toContainText('INACTIVE');
  });

  test('B: Permission grant flow works via UI', async ({ page }) => {
    // Listen for Console logs
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));

    // Mock voice/listen to ensure UI testing reliability
    await page.route('**/voice/listen', async route => {
      // Delay to simulate listening
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, text: 'Simulated Voice Command', status: 'processing' })
      });
    });

    await page.goto('/');

    // Wait for Idle
    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    console.log('B: Clicking core button...');
    
    // T1 CSS Fix: Standard click should now work without JS dispatch
    await page.getByTestId('core-button').click();

    // Expect status to change to LISTENING (immediate UI update)
    console.log('B: Waiting for LISTENING status...');
    await expect(page.getByTestId('app-status')).toHaveText('LISTENING', { timeout: 10000 });

    // Verify session becomes ACTIVE (polling interval is 5s)
    console.log('B: Waiting for ACTIVE session...');
    await expect(page.getByTestId('session-status')).toContainText('ACTIVE', { timeout: 15000 });
  });

  test('C: Plan preview -> approve triggers execution', async ({ page, request }) => {
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    await page.goto('/');

    // Mock Plan Preview (LLM isolation)
    await page.route('**/plan/preview', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
           plan_id: 'mock-plan-id',
           estimated_time_sec: 5,
           plan: {
             id: 'mock-plan-id',
             task: 'Open Notepad',
             steps: [
               { id: '1', description: 'Open Notepad', tool: 'computer', action: 'run', parameters: { command: 'notepad' } }
             ]
           }
        })
      });
    });

    // Mock Plan Approve
    await page.route('**/plan/approve', async route => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'executing', plan_id: 'mock-plan-id' })
        });
    });

    // 1. Grant permission via Backend to ensure session is active
    console.log('C: Granting permission...');
    const grantRes = await request.post(`${BACKEND_URL}/permission/grant`);
    expect(grantRes.ok()).toBeTruthy();

    // Wait for Idle - Input is disabled otherwise
    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    console.log('C: Typing command...');
    // Use data-testid selector
    const input = page.getByTestId('command-input');
    await expect(input).toBeVisible();
    await input.fill('Open Notepad and type hello');
    
    console.log('C: Pressing Enter to Execute...');
    await input.press('Enter');
    
    console.log('C: Waiting for preview panel...');
    const previewPanel = page.getByTestId('plan-preview');
    await expect(previewPanel).toBeVisible({ timeout: 15000 });

    console.log('C: Clicking Approve...');
    await page.getByTestId('plan-approve-button').click();
    
    console.log('C: Waiting for execution status...');
    await expect(page.getByTestId('app-status')).toHaveText(/EXECUTING|PLANNING/, { timeout: 15000 });
  });

  test('D: Settings & Logs', async ({ page }) => {
    await page.goto('/');

    console.log('D: Navigating to Settings...');
    await page.getByTestId('footer-btn-settings').click();
    
    // Check Settings Header
    await expect(page.getByText('⚙️ SETTINGS')).toBeVisible();

    console.log('D: Checking Voice Tab...');
    await page.getByTestId('tab-voice').click();
    await expect(page.getByText('Engine Preference')).toBeVisible();

    console.log('D: Checking Logs Tab...');
    await page.getByTestId('tab-logs').click();
    // Logs component should render timeline (even empty)
    await expect(page.getByText('Execution Timeline')).toBeVisible(); // Timeline Header
  });
});
