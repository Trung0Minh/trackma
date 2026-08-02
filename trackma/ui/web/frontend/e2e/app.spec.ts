import { expect, test } from '@playwright/test';


test('library, discover, and settings remain usable', async ({ page }) => {
  await page.goto('/?mock=1');
  await expect(page.getByRole('heading', { name: 'My library' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary navigation' })).toBeVisible();
  await expect(page.getByText('Home', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Progress', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: /Watching/ })).toHaveAttribute('aria-selected', 'true');

  await expect(page.getByRole('img', { name: /Spy x Family episode progress/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open Spy x Family on AniList' })).toBeVisible();
  await page.getByRole('button', { name: 'Open Spy x Family', exact: true }).click();
  await page.getByRole('button', { name: 'Torrent' }).click();
  const torrentDialog = page.getByRole('dialog', { name: 'Find a release' });
  await expect(torrentDialog).toBeVisible();
  await expect(torrentDialog.getByRole('combobox', { name: 'Category' })).toHaveValue('1_2');
  await expect(torrentDialog.getByText('[MockSubs] Spy x Family - 23 [1080p]')).toBeVisible();
  await torrentDialog.getByRole('button', { name: /Torrent information for/ }).click();
  const releasePreview = page.getByRole('img', { name: 'Release preview' });
  await expect(releasePreview).toHaveCSS('max-width', '100%');
  expect(await releasePreview.evaluate((image) => {
    const content = image.closest('.torrent-info-content');
    return content !== null && image.getBoundingClientRect().width <= content.clientWidth;
  })).toBe(true);
  expect(await page.getByRole('dialog', { name: /MockSubs/ }).evaluate(
    (dialog) => dialog.scrollWidth <= dialog.clientWidth,
  )).toBe(true);
  await page.getByRole('button', { name: 'Close torrent information' }).click();
  await torrentDialog.getByRole('button', { name: 'Close torrent search' }).click();
  await page.getByRole('button', { name: 'Close', exact: true }).click();

  await page.getByRole('button', { name: 'Discover' }).click();
  await page.getByRole('searchbox', { name: 'Search remote catalog' }).fill('Spy');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Spy x Family' })).toBeVisible();

  await page.getByRole('button', { name: 'Settings' }).click();
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Settings categories' })).toBeVisible();
});


test('connection label does not overlap the media selector', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto('/?mock=1');

  const connectionLabel = page.getByText('Engine connected', { exact: true });
  const mediaTypeSelect = page.getByRole('combobox', { name: 'Media type' });
  await expect(connectionLabel).toBeVisible();
  await expect(mediaTypeSelect).toBeVisible();
  expect(await connectionLabel.evaluate((label, select) => {
    const labelBounds = label.getBoundingClientRect();
    const selectBounds = (select as HTMLElement).getBoundingClientRect();
    return labelBounds.right <= selectBounds.left;
  }, await mediaTypeSelect.elementHandle())).toBe(true);
});
