import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

const routes = ['','social-studies/index.html','000005/index.html','library.html','downloads.html','about.html','social-studies/textbook/H04.html','social-studies/textbook/C11.html'];
for (const route of routes) test(`static document: ${route || 'home'}`, async ({ page }) => {
  const active: string[] = [], errors: string[] = [];
  page.on('request', request => { if (['script','xhr','fetch','websocket'].includes(request.resourceType())) active.push(request.url()); });
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto(route);
  expect(response?.status()).toBe(200);
  await expect(page.locator('main h1')).toHaveCount(1);
  await expect(page.locator('script,form,input,button,dialog')).toHaveCount(0);
  await expect(page.getByRole('link', {name:'学習サイト', exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect(active).toEqual([]); expect(errors).toEqual([]);
});
test('course navigation uses ordinary links and preserves all lessons', async ({ page, request }) => {
  const catalog = await (await request.get('catalog.json')).json() as {path:string;section:string;lesson:boolean}[];
  for (const [subject, path, expected] of [['社会','social-studies/index.html',76],['理科','000005/index.html',171]] as const) {
    await page.goto(path);
    const lessons = catalog.filter(p => p.section === subject && p.lesson);
    expect(lessons).toHaveLength(expected);
    for (const p of lessons) expect(await page.locator(`a[href$="${encodeURI(p.path)}"]`).count(), p.path).toBeGreaterThan(0);
  }
  await page.goto('social-studies/textbook/F01.html');
  await page.locator('.page-turn a').last().click();
  await expect(page).toHaveURL(/F02\.html$/);
  await page.goBack(); await expect(page).toHaveURL(/F01\.html$/);
});
test('no JavaScript is required for reading or answer disclosure', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ baseURL, javaScriptEnabled:false, viewport:{width:390,height:844} });
  const page = await context.newPage();
  await page.goto('');
  await page.getByRole('link', {name:'社会の目次',exact:true}).click();
  await page.locator('a[href$="textbook/F01.html"]').first().click();
  const answer = page.locator('.prose details').first();
  await answer.locator('summary').click(); await expect(answer).toHaveAttribute('open','');
  await expect(answer.locator('p').first()).toBeVisible();
  await page.locator('.mobile-course > summary').click();
  await expect(page.locator('.mobile-course nav')).toBeVisible();
  await page.locator('.page-turn a').last().click(); await expect(page).toHaveURL(/F02\.html$/);
  await context.close();
});
test('answer disclosure works from the keyboard', async ({ page }) => {
  await page.goto('social-studies/textbook/F01.html');
  const answer = page.locator('.prose details').first();
  await answer.locator('summary').focus(); await page.keyboard.press('Enter');
  await expect(answer).toHaveAttribute('open','');
  await page.keyboard.press('Enter'); await expect(answer).not.toHaveAttribute('open');
});
test('expanded foundation and subject lessons expose all six answers', async ({ page }) => {
  for (const id of ['F01','F02','F03','F04','G05','H13','C12']) {
    await page.goto(`social-studies/textbook/${id}.html`);
    const answers=page.locator('.prose details');
    await expect(answers).toHaveCount(6);
    await answers.last().locator('summary').click();
    await expect(answers.last().locator('p').first()).toBeVisible();
  }
  await page.goto('social-studies/expansion-sources.html');
  await expect(page.locator('main a[href*="source/expansion/"]')).toHaveCount(0);
  expect(await page.locator('main a[href*="textbook/"]').count()).toBeGreaterThan(0);
});
test('closed answers are visible for printing without changing their open state', async ({ page }) => {
  await page.goto('social-studies/textbook/F01.html');
  const answer = page.locator('.prose details').first();
  await expect(answer).not.toHaveAttribute('open');
  await expect(answer.locator('p').first()).not.toBeVisible();
  await page.emulateMedia({media:'print'});
  await expect(page.locator('.prose .print-answer').first()).toBeVisible();
  await expect(page.locator('.prose .print-answer').first()).toContainText(await answer.innerText());
  await expect(page.locator('.site-header')).not.toBeVisible();
  await expect(answer).not.toHaveAttribute('open');
  await page.emulateMedia({media:'screen'});
  await expect(answer.locator('p').first()).not.toBeVisible();
});
test('narrow viewports do not clip documents or tables', async ({ page }) => {
  for (const width of [320,390,768,1440]) {
    await page.setViewportSize({width,height:900});
    for (const route of ['social-studies/atlas.html','social-studies/textbook/H04.html','downloads.html']) {
      await page.goto(route);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} ${width}`).toBe(true);
    }
  }
});
test('science pictures and ruby are readable', async ({ page, request }) => {
  const catalog = await (await request.get('catalog.json')).json() as {path:string}[];
  const science = catalog.find(p => p.path.includes('/biology/03_'))!;
  await page.goto(encodeURI(science.path));
  await expect(page.locator('.prose')).toContainText('翅');
  await expect(page.locator('ruby').filter({hasText:'翅'}).first().locator('rt')).toHaveText('はね');
  for (const image of await page.locator('.prose img').all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0)).toBe(true);
  }
});
for (const route of ['', 'social-studies/index.html', 'social-studies/textbook/H04.html', 'downloads.html']) test(`accessibility: ${route || 'home'}`, async ({ page }) => {
  await page.goto(route);
  const result = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(result.violations).toEqual([]);
});
test('download links resolve and old review URL is a static notice', async ({ page, request }) => {
  await page.goto('downloads.html');
  for (const link of await page.locator('a[download]').all()) {
    const href = await link.getAttribute('href');
    const response = await request.head(href!); expect(response.ok(), href!).toBe(true);
    expect(Number(response.headers()['content-length'])).toBeGreaterThan(0);
  }
  await page.goto('review.html');
  await expect(page.locator('main')).toContainText('廃止');
  await expect(page.locator('script,button,input')).toHaveCount(0);
});
test('unknown pages have a usable route back to the index', async ({ page }) => {
  const response = await page.goto('does-not-exist-20261001.html');
  expect(response?.status()).toBe(404);
  await expect(page.locator('main h1')).toHaveText('ページが見つかりません');
  await page.locator('main a').click(); await expect(page).toHaveURL(/library\.html$/);
});
