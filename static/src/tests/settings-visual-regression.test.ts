/**
 * Visual regression tests for Settings page.
 * These tests verify actual rendered dimensions and layout, not just DOM structure.
 * This helps catch issues like images being oversized or layout elements being hidden.
 */

import { test, expect } from '@playwright/test';

const SETTINGS_URL = 'http://localhost:8000/settings';
const NAVBAR_IMG_MAX_HEIGHT_PX = 38;
const NAVBAR_IMG_MAX_WIDTH_PX = 1000; // Reasonable max for navbar

test.describe('Settings Page - Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings
    await page.goto(SETTINGS_URL, { waitUntil: 'domcontentloaded' });
    // Wait for React to mount
    await page.waitForTimeout(500);
  });

  test('navbar brand image should be constrained to max height 38px', async ({
    page,
  }) => {
    const navbarImg = page.locator('.navbar-brand img').first();

    // Get computed dimensions
    const dimensions = await navbarImg.evaluate((el: HTMLImageElement) => ({
      offsetHeight: el.offsetHeight,
      offsetWidth: el.offsetWidth,
      computedHeight: window.getComputedStyle(el).height,
      computedMaxHeight: window.getComputedStyle(el).maxHeight,
      isVisible: el.offsetHeight > 0 && el.offsetWidth > 0,
    }));

    expect(dimensions.offsetHeight).toBeLessThanOrEqual(
      NAVBAR_IMG_MAX_HEIGHT_PX + 5,
    );
    expect(dimensions.isVisible).toBe(true);
    expect(
      parseInt(dimensions.computedHeight),
    ).toBeLessThanOrEqual(
      NAVBAR_IMG_MAX_HEIGHT_PX + 5,
    );
  });

  test('navbar should use flexbox layout', async ({ page }) => {
    const navbar = page.locator('.navbar').first();

    const styles = await navbar.evaluate((el: HTMLElement) => {
      const computed = window.getComputedStyle(el);
      return {
        display: computed.display,
        alignItems: computed.alignItems,
      };
    });

    expect(styles.display).toContain('flex');
    expect(styles.alignItems).toBe('center');
  });

  test('settings form controls should be visible and not hidden by images', async ({
    page,
  }) => {
    // Check for key form elements
    const playerNameLabel = page.locator('text=Player name').first();
    const saveButton = page.locator('button:has-text("Save Settings")');
    const backupHeading = page.locator('text=Backup');
    const systemControlsHeading = page.locator('text=System Controls');

    // All should be visible (offsetHeight > 0)
    const labelVisible = await playerNameLabel.isVisible();
    const buttonVisible = await saveButton.isVisible();
    const backupVisible = await backupHeading.isVisible();
    const systemVisible = await systemControlsHeading.isVisible();

    expect(labelVisible).toBe(true);
    expect(buttonVisible).toBe(true);
    expect(backupVisible).toBe(true);
    expect(systemVisible).toBe(true);
  });

  test('no oversized splash/logo images should be present on settings page', async ({
    page,
  }) => {
    const allImages = await page.locator('img').all();

    const oversizedImages = await Promise.all(
      allImages.map(async (img) => {
        const dimensions = await img.evaluate((el: HTMLImageElement) => {
          const rect = el.getBoundingClientRect();
          return {
            height: el.offsetHeight,
            width: el.offsetWidth,
            src: el.src,
            alt: el.alt,
          };
        });

        // Flag images that are suspiciously large (>200px in any dimension)
        // except for legitimately large elements
        const isSuspiciouslyLarge =
          dimensions.height > 200 || dimensions.width > 200;

        return isSuspiciouslyLarge ? dimensions : null;
      }),
    );

    const problematicImages = oversizedImages.filter((img) => img !== null);

    expect(problematicImages).toEqual(
      [],
      `Found oversized images on settings page: ${JSON.stringify(problematicImages)}`,
    );
  });

  test('modal dialogs should constrain image sizes', async ({ page }) => {
    // Find any modal content with images
    const modals = page.locator('.modal-content, [role="dialog"]');
    const modalCount = await modals.count();

    if (modalCount > 0) {
      for (let i = 0; i < modalCount; i++) {
        const modal = modals.nth(i);
        const images = modal.locator('img');
        const imageCount = await images.count();

        for (let j = 0; j < imageCount; j++) {
          const img = images.nth(j);
          const dimensions = await img.evaluate(
            (el: HTMLImageElement) => ({
              height: el.offsetHeight,
              width: el.offsetWidth,
            }),
          );

          // Modal images should not exceed dialog max-width (580px)
          expect(dimensions.width).toBeLessThanOrEqual(580);
        }
      }
    }
  });

  test('page should not have excessive overflow or hidden content', async ({
    page,
  }) => {
    const body = page.locator('body');

    const scrollDimensions = await body.evaluate((el) => {
      return {
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        overflowHidden: window.getComputedStyle(el).overflow === 'hidden',
      };
    });

    // Page should be scrollable if content is larger, not hidden
    if (scrollDimensions.scrollHeight > scrollDimensions.clientHeight) {
      expect(scrollDimensions.overflowHidden).toBe(false);
    }
  });
});
