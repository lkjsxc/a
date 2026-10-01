import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { parse } from 'csv-parse/sync';
import { rubyHTML, rubyMarkdown, stripRuby, glossary } from './ruby.ts';
import { plain } from './render.ts';

// Source normalization is explicit, not an implicit side effect of building the website.
const files = execFileSync('git', ['ls-files', '-z'], { encoding: 'utf8' }).split('\0').filter(Boolean);
const read = (file: string) => readFileSync(file, 'utf8');
let changed = 0, repairedKeywords = 0;
const write = (file: string, value: string) => { if (!existsSync(file) || read(file) !== value) { writeFileSync(file, value); changed++; } };
const csv = (rows: string[][], bom = false) => (bom ? '\ufeff' : '') + rows.map(row => row.map(v => /[",\r\n]/.test(v) ? `"${v.replaceAll('"', '""')}"` : v).join(',')).join('\n') + '\n';
const copy = (text: string) => text.replaceAll('つながり：', '関連語：');
const normalize = (text: string) => {
  const result = rubyHTML(copy(text));
  assert.equal(plain(result), plain(copy(text)), 'Annotations must preserve visible base text');
  return result;
};
const countRuby = (text: string) => [...text.matchAll(/<ruby\b/g)].length;
const beforeCounts = { science: 0, social: 0 };
for (const file of files.filter(f => /^(000005\/reading|social-studies\/textbook)\/.*\.md$/.test(f))) beforeCounts[file.startsWith('000005') ? 'science' : 'social'] += countRuby(read(file));

for (const file of files.filter(f => f.startsWith('000005/') && f.endsWith('.md'))) {
  const old = read(file), updated = rubyMarkdown(copy(old));
  assert.equal(stripRuby(updated), copy(stripRuby(old)), `Markdown base text changed: ${file}`);
  write(file, updated);
}
type ScienceCard = { id: string; front: string; back: string; keywords: string[]; core_first: boolean; core_rank: number | null; [key: string]: unknown };
const masterPath = '000005/data/science_cards_master.json';
const master = JSON.parse(read(masterPath)) as ScienceCard[];
assert.equal(master.length, 857);
const byFront = new Map<string, ScienceCard>();
for (const card of master) {
  const oldFront = plain(card.front);
  assert(!byFront.has(oldFront), `Duplicate science front: ${oldFront}`);
  card.front = normalize(card.front); card.back = normalize(card.back);
  const related = /<div\b[^>]*>[\s\S]*?関連語：[\s\S]*?<\/div>/.exec(card.back)?.[0];
  if (related) {
    const keywords = plain(related).replace(/^.*?関連語：/, '').split('／').map(s => s.trim()).filter(Boolean);
    if (JSON.stringify(keywords) !== JSON.stringify(card.keywords)) { card.keywords = keywords; repairedKeywords++; }
  }
  assert(card.keywords.every(k => !/[<>]/.test(k)), `Invalid keyword: ${card.id}`);
  byFront.set(oldFront, card);
}
assert.equal(master.filter(c => c.core_first).length, 150);
write(masterPath, JSON.stringify(master, null, 2) + '\n');
for (const file of files.filter(f => /^000005\/anki\/science_.*\.(csv|tsv|txt)$/.test(f))) {
  const text = read(file), tab = !file.endsWith('.csv');
  const comments = text.split(/\r?\n/).filter(line => line.startsWith('#'));
  const rows = parse(text, { bom: true, delimiter: tab ? '\t' : ',', quote: tab ? false : '"', comment: '#', skip_empty_lines: true }) as string[][];
  let count = 0;
  for (const row of rows) {
    if (row[0] === 'Front') continue;
    const card = byFront.get(plain(row[0])); assert(card, `Unknown science front in ${file}: ${row[0]}`);
    row[0] = card.front; row[1] = card.back; count++;
  }
  assert.equal(count, file.includes('core_first') ? 150 : 857);
  if (tab) {
    assert(rows.flat().every(v => !/[\t\r\n]/.test(v)), `Unexpected TSV field delimiter: ${file}`);
    write(file, [...comments, ...rows.map(row => row.join('\t'))].join('\n') + '\n');
  } else write(file, csv(rows, text.startsWith('\ufeff')));
}
const masterCSV = parse(read('000005/data/science_cards_master.csv'), { bom: true }) as string[][];
const byID = new Map(master.map(c => [c.id, c]));
for (const row of masterCSV.slice(1)) {
  const card = byID.get(row[0]); assert(card);
  row[8] = card.front; row[9] = card.back; row[10] = card.keywords.join('／');
}
write('000005/data/science_cards_master.csv', csv(masterCSV, true));

const found = new Map<string, { count: number; ids: string[] }>();
for (const c of master) for (const m of (c.front + c.back).matchAll(/<ruby>([\s\S]*?)<\/ruby>/g)) {
  const word = stripRuby(m[0]), item = found.get(word) || { count: 0, ids: [] };
  item.count++; if (!item.ids.includes(c.id)) item.ids.push(c.id); found.set(word, item);
}
write('000005/quality/ruby_glossary.csv', csv([['Term','Reading','Occurrences','ExampleCards'], ...[...found].sort(([a],[b])=>a.localeCompare(b,'ja')).map(([word, value])=>[word,glossary[word],String(value.count),value.ids.slice(0,8).join(' ')])]));
for (const file of ['000001.csv', '000002.csv', '000003.csv']) {
  const text = read(file); const rows = parse(text, { bom: true }) as string[][];
  for (const row of rows) for (let i = 0; i < Math.min(2, row.length); i++) if (/[一-龯々]|<ruby/.test(row[i])) row[i] = normalize(row[i]);
  write(file, csv(rows, text.startsWith('\ufeff')));
}
const basics = JSON.parse(read('000004.json')) as { id: string; front: string; back_html: string; [key: string]: unknown }[];
assert.equal(basics.length, 500);
for (const c of basics) { c.front = normalize(c.front); c.back_html = normalize(c.back_html); }
write('000004.json', JSON.stringify(basics, null, 2) + '\n');
const manifest = JSON.parse(read('000005/manifest.json'));
manifest.title = '小・中学校理科の教材'; manifest.editorial_revision = '2026-10-01';
manifest.ruby_policy = '../editorial/README.md';
write('000005/manifest.json', JSON.stringify(manifest, null, 2) + '\n');
const afterScience = files.filter(f => /^000005\/reading\/.*\.md$/.test(f)).reduce((n, f) => n + countRuby(read(f)), 0);
const audit = { revision: '2026-10-01', policyTerms: Object.keys(glossary).length, scienceCards: master.length, coreCards: 150, beforeReadingRuby: beforeCounts, afterScienceReadingRuby: afterScience, repairedKeywordRecords: repairedKeywords };
// This migration log is historical; later idempotent runs must not erase its baseline.
if (!existsSync('editorial/migration.json')) write('editorial/migration.json', JSON.stringify(audit, null, 2) + '\n');
console.log({ changed, ...audit });
if (process.argv.includes('--checksums')) {
  const names = execFileSync('git', ['ls-files', '-z', '000005'], { encoding: 'utf8' }).split('\0').filter(f => f && f !== '000005/quality/SHA256SUMS.txt' && existsSync(f));
  write('000005/quality/SHA256SUMS.txt', names.map(f => `${createHash('sha256').update(readFileSync(f)).digest('hex')}  ${f.slice(7)}`).join('\n') + '\n');
}
