import { expect, test } from '@playwright/test';


test('library, discover, and settings remain usable', async ({ page }) => {
  await page.goto('/?mock=1');
  await expect(page.getByRole('heading', { name: 'My library' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary navigation' })).toBeVisible();
  await expect(page.getByText('Home', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Progress', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: /Watching/ })).toHaveAttribute('aria-selected', 'true');

  await expect(page.getByRole('img', { name: /Spy x Family episode progress/ })).toBeVisible();
  await page.getByRole('button', { name: 'Open Spy x Family', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Open Spy x Family on AniList' })).toBeVisible();
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
  const yearOptionColors = await page.getByLabel('Year').locator('option').first().evaluate((option) => {
    const style = getComputedStyle(option);
    return { color: style.color, background: style.backgroundColor };
  });
  expect(yearOptionColors.color).not.toBe(yearOptionColors.background);
  expect(yearOptionColors.background).not.toBe('rgba(0, 0, 0, 0)');
  await page.getByRole('searchbox', { name: 'Search catalog' }).fill('Spy');
  await expect(page.getByRole('heading', { name: 'Search results' })).toBeVisible();
  const discoverRegion = page.getByRole('region', { name: 'Browse anime' });
  const detailsButton = page.getByRole('button', { name: 'Open details for Spy x Family' });
  await expect(detailsButton).toBeVisible();
  await expect(discoverRegion).toHaveCSS('transform', 'none');
  await detailsButton.scrollIntoViewIfNeeded();
  const layoutBeforeDetails = await discoverRegion.boundingBox();
  await detailsButton.click();
  const catalogDetails = page.getByRole('dialog');
  await expect(catalogDetails).toHaveCSS('background-color', 'rgb(11, 22, 34)');
  expect(await catalogDetails.evaluate((drawer) => getComputedStyle(drawer.parentElement!).getPropertyValue('--discover-blue').trim())).toBe('#f05c5b');
  await expect(catalogDetails).toContainText('Summer 2026');
  await expect(catalogDetails).toContainText('Manga');
  expect(await discoverRegion.boundingBox()).toEqual(layoutBeforeDetails);
  await catalogDetails.getByRole('button', { name: 'Close catalog details' }).click();

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
