import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { parseHTML } from 'linkedom';
import { route } from './model.ts';
import { glossary, stripRuby } from './ruby.ts';
const root = path.resolve(import.meta.dirname, '..'), out = path.join(root, '_site');
const report = JSON.parse(await readFile(path.join(out, 'build.json'), 'utf8'));
const base = report.base as string, origin = 'https://site.test';
const files = new Set<string>();
async function walk(dir: string) {
  for (const item of await readdir(path.join(out, dir), { withFileTypes: true })) {
    const name = path.posix.join(dir, item.name);
    assert(!item.isSymbolicLink(), `Published symlink: ${name}`);
    if (item.isDirectory()) await walk(name); else files.add(name);
  }
}
await walk('');
const documents = new Map<string, ReturnType<typeof parseHTML>['document']>();
const errors: string[] = [];
for (const file of [...files].filter(f => f.endsWith('.html'))) {
  const text = await readFile(path.join(out, file), 'utf8');
  const { document } = parseHTML(text); documents.set(file, document);
  if (document.documentElement.lang !== 'ja') errors.push(`${file}: missing Japanese language`);
  if (document.querySelectorAll('h1').length !== 1) errors.push(`${file}: expected one h1`);
  if (document.querySelectorAll('main').length !== 1) errors.push(`${file}: expected one main landmark`);
  if (!document.querySelector('title')?.textContent || !document.querySelector('meta[name=description]')?.getAttribute('content')) errors.push(`${file}: missing metadata`);
  const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
  if (ids.length !== new Set(ids).size) errors.push(`${file}: duplicate ids`);
  for (const image of document.querySelectorAll('img')) if (!image.hasAttribute('alt')) errors.push(`${file}: image without alternative text`);
  if (document.querySelector('script,iframe,object,form,input,button,dialog')) errors.push(`${file}: application control or active content`);
  if (/まなびの図書|すこし復習|学習室|つながる理解/.test(text)) errors.push(`${file}: obsolete interface wording`);
  for (const el of document.querySelectorAll('*')) for (const attr of el.attributes) if (/^on/i.test(attr.name) || /^(?:javascript|vbscript):/i.test(attr.value)) errors.push(`${file}: event handler or script URL`);
  for (const ruby of document.querySelectorAll('ruby')) {
    const word = stripRuby(ruby.outerHTML);
    if (ruby.querySelector('ruby') || glossary[word] !== ruby.querySelector('rt')?.textContent) errors.push(`${file}: unreviewed or malformed ruby ${word}`);
  }
}
let links = 0, fragments = 0;
for (const [file, document] of documents) {
  const from = new URL(`${base}${encodeURI(file)}`, origin);
  for (const element of document.querySelectorAll('a[href],img[src],script[src],link[rel=stylesheet],link[rel=icon]')) {
    const raw = element.getAttribute('href') || element.getAttribute('src') || '';
    let url: URL;
    try { url = new URL(raw, from); } catch { errors.push(`${file}: invalid URL ${raw}`); continue; }
    if (url.origin !== origin) continue;
    if (!url.pathname.startsWith(base)) { errors.push(`${file}: URL escapes project base: ${raw}`); continue; }
    const name = decodeURIComponent(url.pathname.slice(base.length)) || 'index.html';
    const target = name.endsWith('/') ? `${name}index.html` : name;
    if (!files.has(target)) { errors.push(`${file}: missing ${target}`); continue; }
    links++;
    if (url.hash && documents.has(target)) {
      const id = decodeURIComponent(url.hash.slice(1));
      if (!documents.get(target)!.getElementById(id)) errors.push(`${file}: missing fragment ${target}#${id}`);
      fragments++;
    }
  }
}
for (const source of report.sources as string[]) assert(files.has(route(source)), `Missing source output: ${source}`);
assert.equal(documents.size, report.pages);
const catalog = JSON.parse(await readFile(path.join(out, 'catalog.json'), 'utf8')) as { path: string; section: string; lesson: boolean }[];
assert.equal(catalog.filter(p => p.section === '社会' && p.lesson).length, 76, 'All 76 original social units must remain');
assert.equal(catalog.filter(p => p.lesson).length, report.lessons);
const expected: Record<string, number> = { social: 2105, science: 857, english: 2286, conversation: 206, art: 62, basics: 500 };
assert.deepEqual(Object.fromEntries(report.decks.map((d: { id: string; count: number }) => [d.id, d.count])), expected, 'All downloadable card counts must remain unchanged');
assert(!files.has('search.json'), 'No application search index');
assert(![...files].some(f => f.startsWith('data/') || /\.(?:m?js|map)$/.test(f)), 'No application payloads');
assert.deepEqual(Object.keys(report.assets), ['css'], 'CSS is the only generated application asset');
const digest = (value: Uint8Array) => createHash('sha256').update(value).digest('hex');
let downloads = 0;
for (const file of files) {
  if (/(^|\/)(source|tools|node_modules|\.git|\.env)(\/|$)/.test(file)) errors.push(`Unexpected published path: ${file}`);
  if (/\.(csv|tsv|txt|xlsx|apkg|zip)$/.test(file)) {
    assert.equal(digest(await readFile(path.join(out, file))), digest(await readFile(path.join(root, file))), `Original download changed: ${file}`);
    downloads++;
  }
}
assert((await stat(path.join(out, report.assets.css))).size < 10000, 'Document CSS budget is 10 KB');
assert((await stat(path.join(out, 'index.html'))).size < 12000, 'Homepage must remain under 12 KB');
assert.equal(errors.length, 0, `${errors.length} site errors:\n${errors.slice(0, 60).join('\n')}`);
console.log(JSON.stringify({ pages: documents.size, checkedLinks: links, checkedFragments: fragments, downloadCopiesMatchSources: downloads, lessons: report.lessons, jsBytes: 0, publishedFiles: files.size }, null, 2));
