# a. まなびの図書室

**[ブラウザーで学ぶ → https://lkjsxc.github.io/a/](https://lkjsxc.github.io/a/)**

基礎から、つながる理解へ。社会・理科の読み物と、英語・美術などのカードをまとめた、登録不要の教材ライブラリです。

[社会の学習室](https://lkjsxc.github.io/a/social-studies/) · [理科の学習室](https://lkjsxc.github.io/a/000005/) · [教材を探す](https://lkjsxc.github.io/a/library.html) · [カードで復習](https://lkjsxc.github.io/a/review.html) · [Anki・教材ダウンロード](https://lkjsxc.github.io/a/downloads.html)

## Webサイトでできること

社会・理科の本文検索、単元を順番に読むナビゲーション、解答を開いて確かめる確認問題、ブラウザーでのカード練習を用意しています。スマートフォンでも読める画面、ダークモード、文字拡大、印刷に対応しています。

「読み終えた」「あとで読む」と最後に開いたページは、このブラウザー内だけに保存します。アカウントや端末間の自動同期はありません。表示設定から学習記録をファイルへ書き出し、別の端末に取り込めます。サイト全体のオフライン動作は保証していないため、オフラインでは教材ZIPやAnkiデータを利用してください。

## 元の教材・データ

| 項目 | 内容 | 形式 |
|---|---|---|
| [000001.csv](000001.csv) | 英日対訳、2,286行 | ヘッダーなし・2列のCSV |
| [000002.csv](000002.csv) | 初級英会話・語彙、206行 | CSV |
| [000003.csv](000003.csv) | 色彩理論・絵画、62行 | CSV |
| [000004.json](000004.json) | 基礎・地理・歴史を扱う500枚のカード | JSON |
| [000005/README.md](000005/README.md) | 小・中学校理科857枚のカードと読み物 | 教材パッケージ |
| [social-studies/README.md](social-studies/README.md) | 中学社会3年分。76単元・Anki 1,293枚・確認228問・総合問題3回 | 読み物・HTML・APKG・CSV・TSV・ZIP |

各教材は独立しています。番号順にすべて読む必要はありません。社会が初めてなら[社会の学習案内](social-studies/study-guide.md)から始めてください。

Ankiを初めて使う場合は、[社会の取り込み案内](social-studies/anki/README.md)・[理科の取り込み案内](000005/anki/IMPORT_GUIDE.md)を先に確認します。同じカードのAPKG・CSV・TSVを重ねて取り込む必要はありません。`000004.json`はAnki用CSVとして直接取り込む形式ではありません。

[社会の教材一式ZIP](social-studies/downloads/social-studies-complete.zip)を展開すると、付属の`index.html`をオフラインで読めます。ZIP内は配布版の画面で、新しいWebサイトの検索や読了記録とは別です。

## サイトの更新・開発

既存の教材データを維持し、Node 24 / TypeScriptで静的なWebサイトを生成します。自宅サーバーや常駐アプリは不要です。**`main`へのpush → 自動検証 → GitHub Pagesへ公開**の順に更新されます。検証が失敗した変更は公開されません。

```sh
npm ci
npm run verify
npx playwright install --with-deps chromium webkit
npm run test:browser
npm run preview
```

プレビューは`http://127.0.0.1:4173/a/`です。生成先`_site/`はコミットしません。ビルド、教材更新時の注意、検証、ロールバックは[サイト開発・運用ガイド](site/README.md)を参照してください。

## 利用にあたって

個人制作の補助教材です。成績や合格を保証せず、教材の内容・数値・制度は学校の最新資料と出典も併せて確認してください。Webサイトの改修は、既存教材すべての内容を改めて監修したことを意味しません。

利用・再配布の条件は[LICENSE](LICENSE)、出典は各教材の案内を確認してください。
