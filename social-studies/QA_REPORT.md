# 検証記録

確認基準日：2026-09-30

この記録は生成プログラムが実際に成功した検査と、その限界を示します。外部の専門家の査読や、模試集団での難易度調査を意味しません。

## 収録数

- lessons: 76

- lesson_counts: {'foundation': 4, 'geography': 27, 'history': 27, 'civics': 18}

- lesson_cards: 2058

- atlas_cards: 47

- anki_cards: 2105

- lesson_questions: 456

- worked_examples: 12

- mock_exams: 3

- mock_questions: 72

- timeline_entries: 119

- reading_characters: 147642

## 増補の適用範囲

2026年10月8日、地理・歴史・公民の72単元を増補しました。基礎4単元も改稿し、全76単元に各6問を収録しました。

本文量は見出し・文章・本文内の参照リンクを含め、空白を除く同一基準で比較しています。カードの説明・問題・生成HTMLのタグを文字数の倍増に含めていません。

{
  "baseline_available": true,
  "baseline_commit": "0e70b2196f1ecbc2bdbbcf0b41d0a5943a5bc10b",
  "measurement": "Each lesson main-text source only; whitespace removed. Excludes vocabulary tables, answers, generated HTML/ruby, duplicate formats and appendices. Headings and inline source links are retained equally in both versions.",
  "before_body_characters": 63416,
  "after_body_characters": 147642,
  "body_ratio": 2.328,
  "before_anki_cards": 1293,
  "after_anki_cards": 2105,
  "before_questions": 228,
  "after_questions": 456,
  "original_note_ids_and_fronts_preserved": true
}

## 自動検査

- 76 expected lessons and order

- unique lesson/card identifiers and normalized keywords

- prerequisite references and acyclic graph

- source reference IDs resolved

- 6 questions per lesson across all 76 lessons

- 3 assessments x 24 questions; each exactly 100 points

- CSV/TSV exact round-trip including HTML and tags

- APKG ZIP CRC and SQLite integrity; note/card/GUID counts

- keyword-only question template

- ruby boundary and nesting regression checks

- worked arithmetic and mock-exam numerical spot checks

## Ankiの検証範囲

APKG内のSQLiteデータベースを開き、ノート数・カード数・一意なGUIDがそれぞれ2,105件で一致し、整合性検査が成功しました。CSV・TSVを再度読み込み、全フィールドの一致を確認しました。

これはデスクトップ・スマートフォンのAnki画面での操作や同期の試験ではありません。更新前にはバックアップを取り、初回は数枚を開いてルビと裏面を確認してください。

## 内容面の点検

本文では、鎖国と断交、署名と発効、公布と施行、総議員と出席議員、割合と実数、政府の立場と現実の管理などを区別して記述しています。歴史の説明を一つの原因や一人の功績だけへ単純化しないよう注意しています。

計算例・グラフの架空データを明示し、総合問題の配点合計と基本計算を確認しました。個々の文の正確さを自動検査だけで保証することはできません。誤りや読みにくさが見つかった場合は、原稿を直して再生成してください。

## 地図

{"world_countries": 177, "japan_prefectures": 47, "source": "Natural Earth 110m admin0 / 10m admin1, public domain"}

原図を47都道府県のコードで抽出したことを検査しています。地図は位置学習用で、一部の離島を省略します。国境・領有権の厳密な判断の資料には用いません。

## 配布形式

Markdown・オフラインHTML・APKG・CSV・TSV・ZIPを生成します。PDFは含みません。印刷にはブラウザーの印刷機能を利用できます。フォントファイルと個人データは含みません。

## Anki実装による取り込み試験

Anki Python 26.9.3 の実際の取り込み処理を、個人データを含まない一時コレクションで実行しました。初回取り込み、同一APKGの再取り込み、内容変更を含む更新、試験用の復習状態の保持を検査しました。詳しい対象ファイルと結果は ANKI_IMPORT_TEST.json に記録しています。デスクトップ画面・実機スマートフォン・同期の試験ではありません。

## ブラウザー表示試験

Chromiumでデスクトップ幅・スマートフォン幅を確認し、単元数、表、スクリプトがないこと、解答の開閉、画像読込、横方向のはみ出し、印刷時の解答表示を検査しました。実機のSafariやAnkiアプリの画面を試験したものではありません。詳細は BROWSER_TEST.json にあります。


## 旧版から増補版への取り込み
旧版1,293ノートから増補版2,105ノートへの取り込みを、個人データを含まない一時コレクションで検証しました。既存ノートの全ID・GUIDの保持、812件の追加、10枚の試験用復習状態の保持、再取り込みによる重複がないことを確認しました。詳細は ANKI_UPGRADE_TEST.json を参照してください。


生成済みのローカルファイル・画像リンクについて、参照先の存在を検査して成功しました。
