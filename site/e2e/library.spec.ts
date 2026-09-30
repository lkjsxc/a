import { test, expect, type Page } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';
import { readFile } from 'node:fs/promises';
import { emptyState, STORAGE_KEY } from '../state.ts';
const first = 'social-studies/textbook/F01.html';
async function openSettings(page: Page) { await page.getByRole('button', { name: '表示設定', exact: true }).click(); }
async function assertNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
}
test('home and native reading route work without additional services', async ({ page }, info) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('./');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('わからない');
  await page.screenshot({ path: info.outputPath('home.png'), fullPage: true });
  await page.getByRole('link', { name: '社会をはじめる →', exact: true }).click();
  await expect(page).toHaveURL(new RegExp('/a/social-studies/textbook/F01.html$'));
  await expect(page.getByRole('heading', { level: 1 })).toContainText('社会は何を');
  const details = page.locator('.prose details').first();
  await expect(details).not.toHaveAttribute('open', '');
  await details.locator('summary').click(); await expect(details).toHaveAttribute('open', '');
  await expect(page.locator('.page-turn')).toContainText('F02');
  await assertNoOverflow(page); expect(errors).toEqual([]);
});
test('reading and navigation remain available with JavaScript disabled', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await context.newPage(); await page.goto('./');
  await expect(page.locator('[data-open-search]')).toBeHidden();
  await page.getByRole('link', { name: '社会をはじめる →', exact: true }).click();
  await expect(page.locator('.prose')).toContainText('朝食の米');
  await page.locator('.prose details summary').first().click();
  await expect(page.locator('.prose details').first()).toHaveAttribute('open', '');
  await context.close();
});
test('Japanese full-text search and Escape return focus', async ({ page }) => {
  await page.goto('./'); await page.getByRole('button', { name: '教材を検索', exact: true }).click();
  await page.getByLabel('教材のタイトル・本文を検索').fill('光合成');
  await expect(page.locator('#search-results li').first()).toBeVisible();
  await page.locator('#search-section').selectOption('理科');
  await expect(page.locator('#search-results li').first()).toContainText('理科');
  await page.locator('#search-input').fill('zzz存在しない教材123');
  await expect(page.locator('#search-status')).toContainText('見つかりませんでした');
  await page.locator('#search-input').fill('<img src=x onerror=alert(1)>');
  await expect(page.locator('#search-status')).toContainText('見つかりませんでした');
  await page.keyboard.press('Escape'); await expect(page.locator('#search-dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: '教材を検索', exact: true })).toBeFocused();
  await page.keyboard.press('/'); await expect(page.locator('#search-input')).toBeFocused();
});
test('search failures are recoverable and do not prevent reading', async ({ page }) => {
  await page.route('**/search.json', route => route.abort());
  await page.goto('./'); await page.getByRole('button', { name: '教材を検索', exact: true }).click();
  await page.locator('#search-input').fill('地理');
  await expect(page.locator('#search-status')).toContainText('読み込めませんでした');
  await page.unroute('**/search.json'); await page.locator('#search-input').fill('光合成');
  await expect(page.locator('#search-results li').first()).toBeVisible();
});
test('read completion, bookmarks, theme and resume survive reload', async ({ page }) => {
  await page.goto(first); await page.locator('[data-complete]').first().click(); await page.locator('[data-bookmark]').first().click();
  await openSettings(page); await page.getByLabel('暗い', { exact: true }).check(); await page.getByLabel('大きめ', { exact: true }).check();
  await page.keyboard.press('Escape'); await page.reload();
  await expect(page.locator('[data-complete]').first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('html')).toHaveAttribute('data-font', 'large');
  await page.goto('library.html'); await page.getByRole('button', { name: 'あとで読む', exact: true }).click();
  await expect(page.locator('[data-library-item]:visible')).toHaveCount(1);
  await page.goto('./'); await expect(page.locator('#continue-panel')).toBeVisible();
  await expect(page.locator('#continue-link')).toHaveAttribute('href', '/a/' + first);
});
test('record export/import is additive and invalid imports leave records untouched', async ({ page }) => {
  await page.goto(first); await page.locator('[data-complete]').first().click(); await openSettings(page);
  const downloadEvent = page.waitForEvent('download'); await page.getByRole('button', { name: '記録を書き出す' }).click();
  const download = await downloadEvent; const content = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(content.completed[first]).toBe(true);
  const incoming = emptyState(); incoming.bookmarks['social-studies/textbook/F02.html'] = true;
  await page.locator('#import-state').setInputFiles({ name: 'record.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(incoming)) });
  await expect(page.locator('#settings-status')).toContainText('取り込みました');
  const before = await page.evaluate(key => localStorage.getItem(key), STORAGE_KEY);
  expect(JSON.parse(before!).completed[first]).toBe(true);
  expect(JSON.parse(before!).bookmarks['social-studies/textbook/F02.html']).toBe(true);
  await page.locator('#import-state').setInputFiles({ name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"version":1,"completed":{"javascript:alert(1)":true}}') });
  await expect(page.locator('#settings-status')).toContainText('取り込めませんでした');
  expect(await page.evaluate(key => localStorage.getItem(key), STORAGE_KEY)).toEqual(before);
});
test('clearing records removes only this project storage key', async ({ page }) => {
  await page.goto(first); await page.evaluate(() => localStorage.setItem('unrelated-site', 'keep'));
  await openSettings(page); await page.getByText('このサイトの記録を消す', { exact: true }).click();
  page.once('dialog', dialog => dialog.accept()); await page.getByRole('button', { name: '記録を消去する', exact: true }).click();
  expect(await page.evaluate(key => localStorage.getItem(key), STORAGE_KEY)).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('unrelated-site'))).toBe('keep');
});
test('blocked localStorage still permits reading, search and session-only progress', async ({ page }) => {
  await page.addInitScript(() => { Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked', 'SecurityError'); } }); });
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(first); await page.locator('[data-complete]').first().click();
  await expect(page.locator('[data-complete]').first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-storage-status]')).toContainText('保存・読み込みできない'); expect(errors).toEqual([]);
});
test('practice reveals answers, finishes five cards and retries mistakes only', async ({ page }) => {
  await page.goto('review.html?set=social&unit=F01'); await page.getByRole('button', { name: '練習をはじめる', exact: true }).click();
  await expect(page.locator('#card-position')).toContainText('F01');
  const fronts: string[] = [];
  for (let i = 0; i < 5; i++) {
    await expect(page.locator('#card-position')).toContainText(`${i + 1} / 5`);
    fronts.push((await page.locator('#card-front').textContent())!);
    await expect(page.locator('#card-answer')).toBeHidden(); await page.locator('#reveal-card').click();
    await expect(page.locator('#card-answer')).toBeVisible(); await page.locator(i === 0 ? '#card-again' : '#card-known').click();
  }
  expect(new Set(fronts).size).toBe(5);
  await expect(page.locator('#review-summary')).toContainText('4枚'); await page.locator('#retry-cards').click();
  await expect(page.locator('#card-position')).toContainText('1 / 1'); await expect(page.locator('#card-front')).toHaveText(fronts[0]);
});
test('card network errors can be retried without stale sessions', async ({ page }) => {
  await page.route('**/data/social.json', route => route.fulfill({ status: 503, body: 'temporarily unavailable' }));
  await page.goto('review.html'); await page.locator('#review-start').click();
  await expect(page.locator('#review-status')).toContainText('再試行');
  await page.unroute('**/data/social.json'); await page.locator('#review-start').click();
  await expect(page.locator('#flashcard')).toBeVisible();
  await page.locator('#review-set').selectOption('science'); await expect(page.locator('#flashcard')).toBeHidden();
  await page.locator('#review-start').click(); await expect(page.locator('#flashcard')).toBeVisible();
});
test('downloads are real files and unknown routes have a useful 404', async ({ page, request }) => {
  await page.goto('downloads.html');
  for (const href of await page.locator('a[download]').evaluateAll(links => links.map(link => (link as HTMLAnchorElement).href))) {
    const response = await request.head(href); expect(response.status(), href).toBe(200);
    expect(Number(response.headers()['content-length']), href).toBeGreaterThan(100);
  }
  const response = await page.goto('does-not-exist.html'); expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('見つかりません');
});
test('320–1440px layouts fit the viewport, including tables and large text', async ({ page }, info) => {
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ['./', first, 'social-studies/index.html', '000005/index.html', 'social-studies/atlas.html', 'library.html', 'review.html', 'downloads.html']) {
      await page.goto(path); await assertNoOverflow(page);
    }
  }
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto(first);
  await openSettings(page); await page.getByLabel('大きめ', { exact: true }).check(); await page.keyboard.press('Escape');
  await assertNoOverflow(page); await page.screenshot({ path: info.outputPath('reader-mobile.png'), fullPage: true });
});
for (const path of ['./', first, 'social-studies/index.html', '000005/index.html', 'library.html', 'downloads.html', 'review.html']) {
  test(`automated accessibility: ${path}`, async ({ page }) => {
    await page.goto(path);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(result.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target) }))).toEqual([]);
  });
}
test('dark mode and dialogs pass automated accessibility checks', async ({ page }) => {
  await page.goto(first); await openSettings(page); await page.getByLabel('暗い', { exact: true }).check();
  let result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))).toEqual([]);
  await page.keyboard.press('Escape'); await page.getByRole('button', { name: '教材を検索', exact: true }).click();
  await page.locator('#search-input').fill('地理'); await expect(page.locator('#search-results li').first()).toBeVisible();
  result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))).toEqual([]);
});
