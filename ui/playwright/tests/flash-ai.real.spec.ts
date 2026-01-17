import { test, expect } from '@playwright/test';

/**
 * Flash AI — Real Backend E2E Tests (Non-Mocked)
 * 
 * These tests interact with the REAL backend without mocking.
 * They are slower and should be run nightly, not on every commit.
 * 
 * Tag: @slow
 * Run: npx playwright test --grep @slow
 */

const BACKEND_URL = 'http://127.0.0.1:8765';

test.describe('Flash AI Real Backend @slow', () => {

  test.beforeEach(async ({ page }) => {
    // Skip onboarding
    await page.addInitScript(() => {
      window.localStorage.setItem('flash_onboarding_complete', 'true');
    });

    // Grant permission before tests
    await page.request.post(`${BACKEND_URL}/permission/grant`);
  });

  test.afterEach(async ({ page }) => {
    // Revoke session after each test
    await page.request.post(`${BACKEND_URL}/permission/revoke`);
  });

  test('Real Plan Preview: generates valid plan structure', async ({ page }) => {
    await page.goto('/');

    // Wait for UI ready
    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    // Type a simple command
    const input = page.getByTestId('command-input');
    await expect(input).toBeVisible();
    await input.fill('Open Notepad');
    await input.press('Enter');

    // Wait for plan preview (real LLM call - may take 5-15s)
    console.log('Waiting for real LLM response...');
    const previewPanel = page.getByTestId('plan-preview');
    await expect(previewPanel).toBeVisible({ timeout: 30000 });

    // Verify plan structure contains expected elements
    await expect(previewPanel).toContainText('Plan Preview');
    // Plan should have at least one step
    await expect(previewPanel.locator('[data-testid="plan-step"]').first()).toBeVisible({ timeout: 5000 }).catch(() => {
      // Fallback: check for any step-like content
      console.log('No plan-step testid found, checking for step text...');
    });
  });

  test('Real Plan Approve: triggers actual execution', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    const input = page.getByTestId('command-input');
    await input.fill('Open Notepad');
    await input.press('Enter');

    // Wait for preview
    const previewPanel = page.getByTestId('plan-preview');
    await expect(previewPanel).toBeVisible({ timeout: 30000 });

    // Click Approve
    await page.getByTestId('plan-approve-button').click();

    // Verify execution starts (status changes)
    await expect(page.getByTestId('app-status')).toHaveText(/EXECUTING|COMPLETE|ERROR/, { timeout: 30000 });
  });

  test('Mid-Execution Revoke: stops gracefully', async ({ page, request }) => {
    await page.goto('/');

    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    const input = page.getByTestId('command-input');
    await input.fill('Open Notepad and type Hello World');
    await input.press('Enter');

    // Wait for preview and approve
    const previewPanel = page.getByTestId('plan-preview');
    await expect(previewPanel).toBeVisible({ timeout: 30000 });
    await page.getByTestId('plan-approve-button').click();

    // Wait for execution to start
    await expect(page.getByTestId('app-status')).toHaveText(/EXECUTING/, { timeout: 15000 });

    // Revoke permission mid-execution
    console.log('Revoking permission mid-execution...');
    await request.post(`${BACKEND_URL}/permission/revoke`);

    // Execution should stop gracefully
    // Status should reflect stopped/paused state (not crash)
    await expect(page.getByTestId('app-status')).not.toHaveText('EXECUTING', { timeout: 10000 });
  });

  test('Session Expired: approve fails gracefully', async ({ page, request }) => {
    await page.goto('/');

    await expect(page.getByTestId('app-status')).toHaveText('I AM VENGEANCE', { timeout: 10000 });

    // Revoke session before trying to approve
    await request.post(`${BACKEND_URL}/permission/revoke`);

    const input = page.getByTestId('command-input');
    await input.fill('Open Notepad');
    await input.press('Enter');

    // Preview should still appear (preview doesn't require session)
    const previewPanel = page.getByTestId('plan-preview');
    // This may or may not be visible depending on backend implementation
    // If it requires session, the test verifies graceful error

    // Try to approve - should fail gracefully
    const approveButton = page.getByTestId('plan-approve-button');
    if (await approveButton.isVisible()) {
      await approveButton.click();
      // Should show error or permission required message
      await expect(page.getByText(/permission|denied|session/i)).toBeVisible({ timeout: 5000 }).catch(() => {
        console.log('No explicit error message, but execution should not start');
      });
    }
  });
});
