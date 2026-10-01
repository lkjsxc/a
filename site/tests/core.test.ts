import { test } from 'node:test';
import assert from 'node:assert/strict';
import { route, escapeHTML } from '../model.ts';
import { clean, plain, localTarget, render } from '../render.ts';
import { rubyHTML, rubyMarkdown, rubyText, stripRuby, glossary } from '../ruby.ts';
import { parse } from 'csv-parse/sync';

const count = (value: string) => [...value.matchAll(/<ruby>/g)].length;
test('routes support project subpaths and Japanese filenames', () => {
  assert.equal(route('000005/reading/README.md'), '000005/reading/index.html');
  assert.equal(route('000005/reading/biology/14_光合成.md'), '000005/reading/biology/14_光合成.html');
  assert.deepEqual(localTarget('../README.md#単元', 'social-studies/textbook/F01.md'), { path: 'social-studies/README.md', suffix: '#単元' });
  assert.deepEqual(localTarget('./%E5%85%89.md', '000005/reading/README.md'), { path: '000005/reading/光.md', suffix: '' });
  assert.equal(localTarget('https://example.com/file.md', 'x.md'), null);
  assert.equal(localTarget('#main', 'x.md'), null);
  assert.throws(() => localTarget('../../oops', 'x.md'));
});
test('sanitization preserves native documents without active content', () => {
  assert.equal(escapeHTML('<a "x">&'), '&lt;a &quot;x&quot;&gt;&amp;');
  const value = clean('<script>alert(1)</script><img src="x.png" onerror="alert(1)"><a href="javascript:alert(1)">x</a><ruby>胚珠<rt>はいしゅ</rt></ruby><details><summary>答え</summary><p>正解</p></details>');
  assert(!value.includes('script')); assert(!value.includes('onerror')); assert(value.includes('<ruby>')); assert(value.includes('<details>'));
  assert.equal(plain('<ruby>胚珠<rp>（</rp><rt>はいしゅ</rt><rp>）</rp></ruby>'), '胚珠');
});
test('renderer retains links, pictures, unique headings, accessible tables', () => {
  const page = render('social-studies/textbook/F01.md', '# Unit\n\n### Intro\n\n## Same\n\n## Same\n\n[Home](../README.md)\n\n![Image](../assets/a.png)\n\n| A | B |\n|---|---|\n|1|2|', new Set(['social-studies/README.md']), new Set(['social-studies/assets/a.png']), new Map([['social-studies/assets/a.png', 'social-studies/assets/a.webp']]), '/a/');
  assert.equal(page.title, 'Unit'); assert.equal(page.lesson, true);
  assert(page.body.includes('href="/a/social-studies/index.html"'));
  assert(page.body.includes('src="/a/social-studies/assets/a.webp"'));
  assert.deepEqual(page.headings.map(h => h.id), ['intro', 'same', 'same-1']);
  assert(page.body.includes('scope="col"')); assert(page.body.includes('role="region"'));
});
test('common terms do not receive automatic kanji readings', () => {
  for (const word of ['地理','歴史','学校','人口','文化','政治','憲法','行政','国会','気候','産業','反射','酸化','電流','水溶液','温度']) assert(!glossary[word], word);
  assert.equal(rubyText('気候と産業、反射と酸化。'), '気候と産業、反射と酸化。');
});
test('hard readings are added without relying on an existing ruby span', () => {
  for (const [word, reading] of Object.entries({ 胚珠:'はいしゅ', 翅:'はね', 絨毛:'じゅうもう', 凡例:'はんれい', 勅許:'ちょっきょ' })) {
    assert.equal(glossary[word], reading);
    assert(rubyText(word).includes(`<rt>${reading}</rt>`));
  }
});
test('whole words, aliases and ambiguous single kanji are protected', () => {
  assert.equal(rubyHTML('二<ruby>酸化<rt>さんか</rt></ruby>炭素'), '二酸化炭素');
  assert.equal(rubyText('明治、明らか、清い、調べる、元の、周り、アレクサンドロス大王'), '明治、明らか、清い、調べる、元の、周り、アレクサンドロス大王');
  const alias = rubyHTML('<ruby>戦後の家電<rt>さんしゅのじんぎ</rt></ruby>（三種の神器）');
  assert(alias.startsWith('戦後の家電（<ruby>三種の神器'));
  const longest = rubyHTML('無脊椎動物と脊椎動物');
  assert(longest.startsWith('<ruby>無脊椎動物')); assert.equal(count(longest), 2);
});
test('first use is scoped to a section, not the whole book', () => {
  const result = rubyHTML('<h2>胚珠</h2><p>胚珠と胚珠。</p><p>胚珠。</p><h2>次</h2><p>胚珠。</p>');
  assert.equal(count(result), 3);
  assert.equal(count(rubyHTML('<div><h2>節1</h2><p>胚珠。</p><h2>節2</h2><p>胚珠。</p></div>')), 2);
});
test('independently readable table cells and answers retain readings', () => {
  const result = rubyHTML('<table><tr><td>胚珠</td><td>胚珠</td></tr></table><details><summary>胚珠</summary><p>胚珠。</p></details>');
  assert.equal(count(result), 4);
});
test('annotations preserve attributes, links, code and base text', () => {
  const value = '<p title="胚珠"><a href="/胚珠.html">胚珠</a> &amp; 翅</p><code>胚珠</code><pre>胚珠</pre>';
  const output = rubyHTML(value);
  assert.equal(plain(output), plain(value));
  assert(output.includes('title="胚珠"')); assert(output.includes('href="/胚珠.html"'));
  assert(output.includes('<code>胚珠</code><pre>胚珠</pre>'));
});
test('Markdown preserves formatting, URLs, code fences and repeated section use', () => {
  const value = '# 胚珠\n\n胚珠と胚珠。\n\n## 次\n胚珠。\n\n[胚珠](胚珠.md) `胚珠`\n\n```html\n胚珠\n```\n';
  const output = rubyMarkdown(value);
  assert.equal(stripRuby(output), value);
  assert(output.includes('[胚珠](胚珠.md) `胚珠`'));
  assert(output.includes('```html\n胚珠\n```'));
  assert.equal(count(output), 3);
});
test('literal ruby examples in code remain literal', () => {
  const snippet = '<ruby>胚珠<rt>はいしゅ</rt></ruby>';
  assert.equal(rubyMarkdown(`\`\`\`html\n${snippet}\n\`\`\``), `\`\`\`html\n${snippet}\n\`\`\``);
  assert.equal(rubyMarkdown(`\`${snippet}\``), `\`${snippet}\``);
  assert.equal(rubyHTML(`<pre>${snippet}</pre>`), `<pre>${snippet}</pre>`);
});
test('normalization is idempotent and does not nest ruby', () => {
  for (const value of ['<p>二<ruby>酸化<rt>さんか</rt></ruby>炭素と胚珠。</p>', '<h2>胚珠</h2><p>胚珠。</p>', '<table><tr><td>翅</td><td>翅</td></tr></table>']) {
    const once = rubyHTML(value); assert.equal(rubyHTML(once), once); assert(!once.includes('<ruby><ruby>'));
  }
  const md = '# 胚珠\n\n胚珠と胚珠。\n\n## 節\n胚珠。';
  assert.equal(rubyMarkdown(rubyMarkdown(md)), rubyMarkdown(md));
});
test('Anki TSV accepts unquoted HTML and CSV handles quotes', () => {
  assert.deepEqual(parse('#html:true\nfront\t<div class="back">answer</div>\ttag\n', { delimiter:'\t', quote:false, comment:'#' }), [['front','<div class="back">answer</div>','tag']]);
  assert.deepEqual(parse('front,"<div class=""back"">answer</div>",tag\n'), [['front','<div class="back">answer</div>','tag']]);
});
