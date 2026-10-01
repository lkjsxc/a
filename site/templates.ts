import { escapeHTML as e, type Page, type Deck } from './model.ts';
import { rubyText } from './ruby.ts';

export function templates(base: string, siteURL: string, revision: string, pages: Page[], decks: Deck[], assets: { css: string }) {
  const url = (path = '') => `${base}${encodeURI(path)}`;
  const a = (path: string, label: string) => `<a href="${url(path)}">${e(label)}</a>`;
  const lessons = pages.filter(p => p.lesson);
  const subjectPath = (section: string) => section === '社会' ? 'social-studies/index.html' : '000005/index.html';
  const list = (items: Page[]) => `<ul class="document-list">${items.map(p => `<li>${a(p.path, p.title)}</li>`).join('')}</ul>`;
  function shell(title: string, body: string, path: string, description = '社会・理科の本文、確認問題、Anki用データを掲載しています。', noindex = false) {
    const titleText = title === '学習サイト' ? title : `${title} | 学習サイト`;
    return `<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>${e(titleText)}</title><meta name="description" content="${e(description)}"><meta name="referrer" content="strict-origin-when-cross-origin">${noindex ? '<meta name="robots" content="noindex">' : ''}<link rel="canonical" href="${e(new URL(path, siteURL).href)}"><meta property="og:title" content="${e(titleText)}"><meta property="og:description" content="${e(description)}"><meta property="og:type" content="website"><meta property="og:locale" content="ja_JP"><meta property="og:url" content="${e(new URL(path, siteURL).href)}"><link rel="icon" href="${url('assets/favicon.svg')}" type="image/svg+xml"><link rel="stylesheet" href="${url(assets.css)}"></head><body><a class="skip" href="#main">本文へ移動</a><header class="site-header"><a class="site-name" href="${url()}">学習サイト</a><nav aria-label="メイン">${a('social-studies/index.html', '社会')}${a('000005/index.html', '理科')}${a('library.html', '教材一覧')}${a('downloads.html', 'ダウンロード')}</nav></header>${body}<footer class="site-footer"><nav aria-label="フッター">${a('about.html', 'このサイトについて')}${a('social-studies/SOURCES.html', '社会の出典')}${a('000005/sources/SOURCES.html', '理科の出典')}<a href="https://github.com/lkjsxc/a">GitHub</a>${a('LICENSE', 'ライセンス')}</nav></footer></body></html>`;
  }
  function indexBody(section: string) {
    const course = lessons.filter(p => p.section === section);
    const groups = [...new Set(course.map(p => p.group))];
    return `<nav class="section-index" aria-label="${e(section)}の分野">${groups.map((name, i) => `<a href="#group-${i}">${e(name)}</a>`).join('')}</nav>${groups.map((name, i) => `<section aria-labelledby="group-${i}"><h2 id="group-${i}">${e(name)}</h2>${list(course.filter(p => p.group === name))}</section>`).join('')}`;
  }
  function resources(section: string) {
    return section === '社会' ? `<h2 id="resources">資料・問題</h2><ul><li>${a('social-studies/study-guide.html', '学習の進め方')}</li><li>${a('social-studies/atlas.html', '地図・統計資料')}</li><li>${a('social-studies/timeline.html', '年表')}</li><li>${a('social-studies/glossary.html', '用語集')}</li><li>${a('social-studies/workbook.html', '単元別確認問題')}</li><li>${a('social-studies/coverage.html', '学習範囲')}</li>${[1, 2, 3].map(n => `<li>総合問題 ${n}：${a(`social-studies/mock-0${n}.html`, '問題')} ／ ${a(`social-studies/mock-0${n}-answers.html`, '解答・解説')}</li>`).join('')}</ul>` : `<h2 id="resources">資料</h2><ul><li>${a('000005/reading/00_start_here/learning_plan.html', '学習計画')}</li><li>${a('000005/reading/00_start_here/core_first_150.html', '基礎150枚のカード')}</li><li>${a('000005/reading/01_skills/calculation_strategy.html', '計算問題の解き方')}</li><li>${a('000005/reading/01_skills/experiment_reasoning.html', '実験結果の考察')}</li><li>${a('000005/anki/IMPORT_GUIDE.html', 'Ankiの取り込み手順')}</li></ul>`;
  }
  function courseNav(page: Page) {
    const course = lessons.filter(p => p.section === page.section);
    const groups = [...new Set(course.map(p => p.group))];
    return `<nav aria-label="${page.section}の単元">${a(subjectPath(page.section), `${page.section}の目次`)}${groups.map(group => `<details${group === page.group ? ' open' : ''}><summary>${e(group)}</summary><ul>${course.filter(p => p.group === group).map(p => `<li><a href="${url(p.path)}"${p.path === page.path ? ' aria-current="page"' : ''}>${e(p.title)}</a></li>`).join('')}</ul></details>`).join('')}</nav>`;
  }
  function reader(page: Page) {
    if (page.source === 'social-studies/README.md' || page.source === '000005/README.md') {
      return shell(page.section, `<main id="main" class="document"><h1>${page.section}</h1><p>${page.section === '社会' ? '中学校3年間の地理・歴史・公民を、基礎から順に学ぶ教材です。' : '小学校・中学校の理科を、学年・分野別にまとめています。'}</p>${indexBody(page.section)}${resources(page.section)}<section class="package-notes"><h2>教材の概要</h2><div class="prose">${page.body}</div></section></main>`, page.path);
    }
    const course = lessons.filter(p => p.section === page.section);
    const at = course.findIndex(p => p.path === page.path);
    const previous = at > 0 ? course[at - 1] : undefined, next = at >= 0 ? course[at + 1] : undefined;
    return shell(page.title, `<div class="reader-layout"><aside class="sidebar">${courseNav(page)}</aside><main id="main" class="reader-main"><nav class="breadcrumbs" aria-label="現在地">${a('', 'ホーム')}<span>/</span>${a(subjectPath(page.section), page.section)}<span>/</span><span>${e(page.group)}</span></nav><details class="mobile-course"><summary>単元一覧</summary>${courseNav(page)}</details><article><header class="article-header"><h1>${rubyText(page.title)}</h1></header>${page.headings.length ? `<nav class="page-toc" aria-label="このページの目次"><h2>目次</h2><ul>${page.headings.map(h => `<li><a href="#${e(h.id)}">${e(h.text)}</a></li>`).join('')}</ul></nav>` : ''}<div class="prose">${page.body}</div>${previous || next ? `<nav class="page-turn" aria-label="前後の単元">${previous ? `<div>前：${a(previous.path, previous.title)}</div>` : ''}${next ? `<div>次：${a(next.path, next.title)}</div>` : ''}</nav>` : ''}<p class="source-link"><a href="https://github.com/lkjsxc/a/blob/main/${encodeURI(page.source)}">原稿</a> ／ <a href="https://github.com/lkjsxc/a/issues/new?title=${encodeURIComponent(`教材の修正：${page.title}`)}">誤りの報告</a></p></article></main></div>`, page.path, page.title);
  }
  function home() {
    return shell('学習サイト', `<main id="main" class="document"><h1>学習サイト</h1><p>社会・理科の本文、確認問題、Anki用データを掲載しています。</p><h2>社会</h2><p>中学校3年間の地理・歴史・公民。基礎から高校受験までを扱います。</p><ul><li>${a('social-studies/index.html', '社会の目次')}</li><li>${a('social-studies/textbook/F01.html', 'F01 社会の学習を始める')}</li><li>${a('social-studies/study-guide.html', '学習の進め方')}</li></ul><h2>理科</h2><p>小学校・中学校の物理・化学・生物・地学。学年別の教材と実験・計算の解説を掲載しています。</p><ul><li>${a('000005/index.html', '理科の目次')}</li><li>${a('000005/reading/00_start_here/learning_plan.html', '学習計画')}</li></ul><h2>教材一覧・配布データ</h2><ul><li>${a('library.html', 'すべての教材')}</li><li>${a('downloads.html', 'Anki用データ・教材のダウンロード')}</li></ul><p>英単語・英会話・美術などのカードデータもダウンロードページに掲載しています。</p></main>`, 'index.html');
  }
  function library() {
    return shell('教材一覧', `<main id="main" class="document"><h1>教材一覧</h1><p>科目別の本文と資料の一覧です。ページ内の語句はブラウザーの検索機能で検索できます。</p><nav class="section-index" aria-label="科目">${a('social-studies/index.html', '社会の目次')}${a('000005/index.html', '理科の目次')}</nav>${(['社会', '理科'] as const).map(section => `<h2>${section}</h2>${[...new Set(pages.filter(p => p.section === section).map(p => p.group))].map(group => `<h3>${e(group)}</h3>${list(pages.filter(p => p.section === section && p.group === group))}`).join('')}`).join('')}</main>`, 'library.html');
  }
  function review() {
    return shell('カードデータ', `<main id="main" class="document"><h1>カードデータ</h1><p>ブラウザー内のカード練習機能は廃止しました。カードはAnki用データとして配布しています。</p><p>${a('downloads.html', 'ダウンロードページ')}</p><p>${a('library.html', '教材一覧')}</p></main>`, 'review.html', undefined, true);
  }
  function downloads(sizes: Map<string, number>) {
    const file = (path: string, label: string) => `<li><a href="${url(path)}" download>${e(label)}</a> <span class="file-size">（${((sizes.get(path) || 0) / 1024 / 1024).toFixed(2)} MB）</span></li>`;
    return shell('ダウンロード', `<main id="main" class="document"><h1>ダウンロード</h1><h2>社会</h2><p>APKG・CSV・TSVは同じ${decks.find(d => d.id === 'social')!.cards.length.toLocaleString('ja-JP')}枚のカードです。いずれか一つを取り込んでください。</p><ul>${file('social-studies/anki/social-studies.apkg', 'Ankiパッケージ（APKG）')}${file('social-studies/anki/cards.csv', 'カード（CSV）')}${file('social-studies/anki/cards.tsv', 'カード（TSV）')}${file('social-studies/downloads/social-studies-complete.zip', 'オフライン教材一式（ZIP）')}</ul><p>${a('social-studies/anki/index.html', '取り込み手順と更新時の注意')}</p><p>ZIPは展開後、index.htmlを開いて利用します。</p><h2>理科</h2><p>全${decks.find(d => d.id === 'science')!.cards.length}枚。基礎150枚は全カードの一部です。重複して取り込まないよう注意してください。</p><ul>${file('000005/anki/science_core_first_150.tsv', '基礎150枚（TSV）')}${file('000005/anki/science_front_back.tsv', '全カード・表裏（TSV）')}${file('000005/anki/science_tagged.tsv', '全カード・タグ付き（TSV）')}${file('000005/data/science_cards_master.csv', '編集用データ（CSV・全項目）')}</ul><p>${a('000005/anki/IMPORT_GUIDE.html', '理科の取り込み手順')}</p><h2>英語・美術・基礎</h2><ul>${file('000001.csv', '英単語・対訳（CSV）')}${file('000002.csv', '初級英会話・語彙（CSV）')}${file('000003.csv', '色彩理論・絵画（CSV）')}${file('000004.json', '基礎・地理・歴史カード（JSON）')}</ul><p>CSVは表・裏の2列です。JSONは構造化データであり、Ankiに直接取り込む形式ではありません。</p></main>`, 'downloads.html');
  }
  function about() {
    return shell('このサイトについて', `<main id="main" class="document prose"><h1>このサイトについて</h1><h2>利用方法</h2><p>科目の目次から教材を開いてください。検索、ブックマーク、文字の拡大、印刷にはブラウザーの標準機能を利用できます。確認問題の解答はクリックまたはキーボードで開けます。</p><h2>サイトの構成</h2><p>HTMLとCSSで構成した静的サイトです。サイト独自のJavaScript、アカウント、学習記録、アクセス解析ツールはありません。</p><p>旧版で保存したブラウザー内の学習記録は読み取りません。削除する場合はブラウザーのサイトデータ管理を使用してください。同じドメインの他のサイトのデータも削除される場合があります。</p><h2>ルビ</h2><p>一般的な語には原則として付けず、難読の人名・地名・歴史用語・理科用語に付けています。本文では節の初出を基本とし、用語表や確認問題、カードは個別に読めるよう扱います。読みが文脈で変わる語に、機械的に読みを補うことは避けています。</p><h2>教材の位置づけ</h2><p>個人制作の補助教材です。学校や入試主催者の公式教材ではなく、成績や合格を保証するものではありません。教材の誤りや制度・統計の更新については、${a('social-studies/SOURCES.html', '社会の出典')}、${a('000005/sources/SOURCES.html', '理科の出典')}、学校の資料も確認してください。</p><p>理科の概念図は、正確な縮尺や形状を示すとは限りません。</p><h2>配信・利用条件</h2><p>GitHub Pagesから配信しています。配信事業者による情報の取り扱いは<a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHubのプライバシーステートメント</a>を確認してください。</p><p>教材の利用条件は${a('LICENSE', 'Apache License 2.0')}、第三者資料の利用条件は各出典に従います。</p><p class="source-link">公開リビジョン：<code>${e(revision)}</code></p></main>`, 'about.html');
  }
  function notFound() {
    return shell('ページが見つかりません', `<main id="main" class="document"><h1>ページが見つかりません</h1><p>URLを確認するか、${a('library.html', '教材一覧')}から開いてください。</p></main>`, '404.html', undefined, true);
  }
  return { reader, home, library, review, downloads, about, notFound };
}
