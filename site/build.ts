import { readdir, readFile, writeFile, mkdir, rm, copyFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { parse } from 'csv-parse/sync';
import { build } from 'esbuild';
import sharp from 'sharp';
import { clean, render } from './render.ts';
import { type Page, type Deck, route, escapeHTML } from './model.ts';
import { templates } from './templates.ts';

const root = path.resolve(import.meta.dirname, '..'), out = path.join(root, '_site');
const siteURL = process.env.SITE_URL || 'https://lkjsxc.github.io/a/';
const site = new URL(siteURL);
if (!['https:', 'http:'].includes(site.protocol) || !site.pathname.endsWith('/') || site.search || site.hash || /[^a-zA-Z0-9/_-]/.test(site.pathname)) throw new Error('SITE_URL must be an absolute URL with a safe trailing-slash path');
const base = site.pathname;
const revision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
const files: string[] = [];
async function walk(dir: string) {
  for (const item of (await readdir(path.join(root, dir), { withFileTypes: true })).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const name = `${dir}/${item.name}`;
    if (item.isSymbolicLink()) throw new Error(`Refusing symlink in published content: ${name}`);
    if (item.name.startsWith('.') || ['source', 'tools', '__pycache__'].includes(item.name)) continue;
    if (item.isDirectory()) await walk(name); else files.push(name);
  }
}
await walk('social-studies'); await walk('000005');
files.push('000001.csv', '000002.csv', '000003.csv', '000004.json', 'LICENSE');
const markdown = files.filter(f => f.endsWith('.md'));
const sources = new Set(markdown);
const copied = files.filter(f => /\.(csv|tsv|txt|json|xlsx|apkg|zip|svg|png|jpe?g|webp)$/.test(f) || /(^|\/)LICENSE$/.test(f));
// Publish only an explicit allowlist, never the repository, tools, tokens, or git metadata.
await rm(out, { recursive: true, force: true }); await mkdir(out, { recursive: true });
const put = async (name: string, content: string | Uint8Array) => { await mkdir(path.dirname(path.join(out, name)), { recursive: true }); await writeFile(path.join(out, name), content); };
const sizes = new Map<string, number>();
for (const name of copied) {
  await mkdir(path.dirname(path.join(out, name)), { recursive: true });
  await copyFile(path.join(root, name), path.join(out, name));
  sizes.set(name, (await stat(path.join(root, name))).size);
}
const images = new Map<string, string>();
for (const name of copied.filter(f => /\.(png|jpe?g)$/.test(f))) {
  const target = name.replace(/\.(png|jpe?g)$/, '.webp');
  await sharp(path.join(root, name)).resize({ width: 1400, withoutEnlargement: true }).webp({ quality: 82 }).toFile(path.join(out, target));
  images.set(name, target);
}
const decks: Deck[] = [];
for (const config of [
  { id: 'social', name: '社会・3年間', file: 'social-studies/anki/cards.csv', delimiter: ',' },
  { id: 'science', name: '理科・小中学校', file: '000005/anki/science_tagged.tsv', delimiter: '\t' },
  { id: 'english', name: '英単語・対訳', file: '000001.csv', delimiter: ',' },
  { id: 'conversation', name: '初級英会話・語彙', file: '000002.csv', delimiter: ',' },
  { id: 'art', name: '色彩理論・絵画', file: '000003.csv', delimiter: ',' },
]) {
  const data = await readFile(path.join(root, config.file), 'utf8');
  const rows = parse(data, { delimiter: config.delimiter, quote: config.delimiter === '\t' ? false : '"', bom: true, skip_empty_lines: true, comment: '#', relax_column_count: true }) as string[][];
  const cards = rows.filter(row => row.length >= 2 && row[0] && row[1]).map(row => ({ front: clean(row[0]), back: clean(row[1]), tags: row[2] || '' }));
  if (!cards.length) throw new Error(`No cards: ${config.file}`);
  decks.push({ id: config.id, name: config.name, cards });
}
const oldCards = JSON.parse(await readFile(path.join(root, '000004.json'), 'utf8')) as { front: string; back_html: string; tags: string }[];
decks.push({ id: 'basics', name: '基礎・地理・歴史', cards: oldCards.map(c => ({ front: clean(c.front), back: clean(c.back_html), tags: c.tags })) });
for (const d of decks) await put(`data/${d.id}.json`, JSON.stringify(d.cards));
const pages: Page[] = [];
const publishedTargets = new Set([...copied, ...markdown.map(route)]);
for (const source of markdown) pages.push(render(source, await readFile(path.join(root, source), 'utf8'), sources, publishedTargets, images, base));
const scienceOrder = ['00_start_here', '01_skills', '02_grade_maps', 'inquiry', 'physics', 'chemistry', 'biology', 'earth_science'];
const rank = (p: Page) => p.section === '社会' ? ({ F: 0, G: 1, H: 2, C: 3 }[path.basename(p.path)[0]] ?? 4) : 5 + (scienceOrder.indexOf(p.source.split('/')[2]) + 1) / 10;
const startRank = (p: Page) => p.source.endsWith('/learning_plan.md') ? 0 : p.source.endsWith('/how_to_read_cards.md') ? 1 : 2;
pages.sort((a, b) => rank(a) - rank(b) || startRank(a) - startRank(b) || a.source.localeCompare(b.source, 'en'));
const js = await build({ entryPoints: [path.join(root, 'site/app.ts')], bundle: true, write: false, minify: true, target: ['es2022'], format: 'esm', legalComments: 'none' });
const script = js.outputFiles![0].contents, css = await readFile(path.join(root, 'site/style.css'));
const hash = (value: Uint8Array) => createHash('sha256').update(value).digest('hex').slice(0, 12);
const assets = { js: `assets/app.${hash(script)}.js`, css: `assets/style.${hash(css)}.css` };
await put(assets.js, script); await put(assets.css, css);
await put('assets/favicon.svg', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#225346"/><text x="13" y="46" font-family="Georgia,serif" font-size="50" font-weight="bold" fill="#fffaf0">a.</text></svg>');
const t = templates(base, site.href, revision, pages, decks, assets);
for (const p of pages) await put(p.path, t.reader(p));
for (const [name, html] of Object.entries({ 'index.html': t.home(), 'library.html': t.library(), 'review.html': t.review(), 'downloads.html': t.downloads(sizes), 'about.html': t.about(), '404.html': t.notFound() })) await put(name, html);
const searchable = pages.filter(p => !/\/(quality|tables|assets)\//.test(p.path) && !/QA_REPORT|textbook\.html|glossary\.html|workbook\.html/.test(p.path));
await put('search.json', JSON.stringify(searchable.map(({ path, title, section, text }) => ({ path, title, section, text }))));
await put('catalog.json', JSON.stringify(pages.map(({ path, title, section, lesson }) => ({ path, title, section, lesson }))));
await put('build.json', JSON.stringify({ revision, base, pages: pages.length + 6, lessons: pages.filter(p => p.lesson).length, decks: decks.map(d => ({ id: d.id, count: d.cards.length })), assets, images: images.size, sources: markdown }, null, 2));
await put('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['', 'library.html', 'downloads.html', 'about.html', ...searchable.map(p => p.path)].map(p => `<url><loc>${escapeHTML(new URL(p, site).href)}</loc></url>`).join('')}</urlset>`);
await put('.nojekyll', '');
console.log(JSON.stringify({ revision, base, pages: pages.length + 6, lessons: pages.filter(p => p.lesson).length, decks: decks.map(d => ({ id: d.id, count: d.cards.length })), optimizedImages: images.size, jsBytes: script.length, cssBytes: css.length }, null, 2));
