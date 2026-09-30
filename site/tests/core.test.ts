import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalize, route, search, escapeHTML } from '../model.ts';
import { safePage, emptyState, parseState, mergeState } from '../state.ts';
import { clean, plain, localTarget, render } from '../render.ts';
import { shuffled } from '../review.ts';
import { parse } from 'csv-parse/sync';

test('routes support project subpaths and Japanese filenames', () => {
  assert.equal(route('000005/reading/README.md'), '000005/reading/index.html');
  assert.equal(route('000005/reading/biology/14_光合成.md'), '000005/reading/biology/14_光合成.html');
  assert.deepEqual(localTarget('../README.md#単元', 'social-studies/textbook/F01.md'), { path: 'social-studies/README.md', suffix: '#単元' });
  assert.deepEqual(localTarget('./%E5%85%89.md', '000005/reading/README.md'), { path: '000005/reading/光.md', suffix: '' });
  assert.equal(localTarget('https://example.com/file.md', 'x.md'), null);
  assert.equal(localTarget('#main', 'x.md'), null);
  assert.throws(() => localTarget('../../oops', 'x.md'));
});
test('Japanese search normalizes width/case/kana and applies AND/subject filters', () => {
  assert.equal(normalize(' ＡＢＣ　カタカナ '), 'abc かたかな');
  const items = [
    { path: '1', title: '光合成', text: '植物 光 エネルギー', section: '理科' },
    { path: '2', title: '農業', text: '植物 光合成 エネルギー', section: '社会' },
  ];
  assert.equal(search(items, '光合成')[0].path, '1');
  assert.equal(search(items, '光合成 エネルギー', '社会')[0].path, '2');
  assert.deepEqual(search(items, '無関係'), []); assert.deepEqual(search(items, '  '), []);
  assert.equal(search(Array.from({ length: 50 }, (_, i) => ({ ...items[0], path: String(i) })), '光').length, 30);
});
test('HTML escapes titles and strips active content while preserving Japanese ruby and details', () => {
  assert.equal(escapeHTML('<a "x">&'), '&lt;a &quot;x&quot;&gt;&amp;');
  const value = clean('<script>alert(1)</script><img src="x.png" onerror="alert(1)"><a href="javascript:alert(1)">x</a><ruby>地理<rt>ちり</rt></ruby><details><summary>答え</summary><p>正解</p></details>');
  assert(!value.includes('script')); assert(!value.includes('onerror')); assert(value.includes('<ruby>')); assert(value.includes('<details>'));
  assert.equal(plain('<ruby>地理<rp>（</rp><rt>ちり</rt><rp>）</rp></ruby>'), '地理');
  assert(plain('<ruby>地理<rt>ちり</rt></ruby>', true).includes('ちり'));
});
test('renderer rewrites local links, optimizes pictures, creates unique headings and accessible tables', () => {
  const page = render('social-studies/textbook/F01.md', '# Unit\n\n### Intro\n\n## Same\n\n## Same\n\n[Home](../README.md)\n\n![Image](../assets/a.png)\n\n| A | B |\n|---|---|\n|1|2|', new Set(['social-studies/README.md']), new Set(['social-studies/assets/a.png']), new Map([['social-studies/assets/a.png', 'social-studies/assets/a.webp']]), '/a/');
  assert.equal(page.title, 'Unit'); assert.equal(page.lesson, true);
  assert(page.body.includes('href="/a/social-studies/index.html"'));
  assert(page.body.includes('src="/a/social-studies/assets/a.webp"'));
  assert.deepEqual(page.headings.map(h => h.id), ['intro', 'same', 'same-1']);
  assert(page.body.includes('scope="col"')); assert(page.body.includes('role="region"'));
});
test('state roundtrip keeps identity and validates dangerous paths', () => {
  const state = emptyState(); state.completed['social-studies/textbook/F01.html'] = true;
  state.bookmarks['000005/reading/biology/14_光合成.html'] = true;
  assert.deepEqual(parseState(JSON.stringify(state)), state);
  for (const path of ['//evil.test/', 'javascript:alert(1)', '../a.html', 'social-studies/../../x.html', 'social-studies/%2e%2e/x.html', 'social-studies/a.html?x=1', '__proto__']) assert(!safePage(path), path);
});
test('invalid imports fail atomically with bounded size/shape', () => {
  for (const raw of ['null', '{}', '[]', 'broken', ' '.repeat(256001), JSON.stringify({ ...emptyState(), completed: [] }), JSON.stringify({ ...emptyState(), theme: '<script>' }), JSON.stringify({ ...emptyState(), last: { path: 'evil', title: 'x', at: 1 } }), JSON.stringify({ ...emptyState(), completed: { 'social-studies/x.html': false } })]) assert.throws(() => parseState(raw));
});
test('import merges records and newest last page without overwriting current preferences', () => {
  const current = emptyState(), incoming = emptyState();
  current.theme = 'dark'; current.font = 'large';
  current.completed['social-studies/textbook/F01.html'] = true;
  incoming.completed['social-studies/textbook/F02.html'] = true;
  current.last = { path: 'social-studies/textbook/F01.html', title: '1', at: 1 };
  incoming.last = { path: 'social-studies/textbook/F02.html', title: '2', at: 2 };
  const result = mergeState(current, incoming);
  assert.equal(Object.keys(result.completed).length, 2); assert.equal(result.theme, 'dark'); assert.equal(result.font, 'large'); assert.equal(result.last?.at, 2);
  assert.equal(Object.keys(current.completed).length, 1);
});
test('shuffle preserves the source, multiplicity and all items', () => {
  const input = [1, 2, 3, 4, 5]; const output = shuffled(input, () => 0);
  assert.deepEqual(input, [1, 2, 3, 4, 5]); assert.deepEqual([...output].sort(), input); assert.notDeepEqual(output, input);
  assert.deepEqual(shuffled([]), []); assert.deepEqual(shuffled([1]), [1]);
});
test('Anki TSV accepts unquoted HTML attributes; CSV accepts escaped quotes', () => {
  assert.deepEqual(parse('#html:true\nfront\t<div class="back">answer</div>\ttag\n', { delimiter: '\t', quote: false, comment: '#' }), [['front', '<div class="back">answer</div>', 'tag']]);
  assert.deepEqual(parse('front,"<div class=""back"">answer</div>",tag\n'), [['front', '<div class="back">answer</div>', 'tag']]);
});
