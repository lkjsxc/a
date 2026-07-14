# ディレクトリ案内

```text
science_master_2026/
├── README.md                         # 教材全体の入口・実数集計
├── DIRECTORY_MAP.md                   # この案内
├── manifest.json                      # 版・枚数・形式の機械可読情報
├── science_cards.xlsx                 # 検索・編集・集計用ワークブック
├── assets/
│   ├── README.md                     # 図版26点のプロンプト・配置・QA台帳
│   └── images/                       # 本文に掲載する不透明PNG
│       ├── overview/                 # 教材全体の概観図1点
│       ├── inquiry/                  # 探究の概要・主題図5点
│       ├── physics/                  # 物理の概要・主題図5点
│       ├── chemistry/                # 化学の概要・主題図5点
│       ├── biology/                  # 生物の概要・主題図5点
│       └── earth_science/            # 地学の概要・主題図5点
├── anki/
│   ├── science_core_first_150.tsv     # 最初に学ぶ厳選150枚
│   ├── science_front_back.tsv         # 表・裏2列、推奨最小版
│   ├── science_tagged.tsv             # 領域・学年・優先度タグ付き
│   ├── science_front_back.csv         # UTF-8 CSV
│   ├── IMPORT_GUIDE.md                # 読み込み手順
│   └── template/                      # 任意のカードCSS・裏面テンプレート
├── data/
│   ├── science_cards_master.json      # 全メタデータ
│   └── science_cards_master.csv       # 全メタデータ表
├── tables/
│   ├── core_first_150_front_back.md   # 最初の150枚の表裏一表
│   ├── all_cards_front_back.md        # 全カードを表・裏の一表に統合
│   └── all_cards_with_metadata.md     # ID等を加えた監査表
├── reading/
│   ├── 00_start_here/                 # 学習計画・全領域の物語
│   ├── 01_skills/                     # 実験・計算・誤解対策
│   ├── 02_grade_maps/                 # 小3〜中3の学年別体系マップ
│   ├── inquiry/                       # 探究カードの単元別読み物
│   ├── physics/                       # 物理の単元別読み物
│   ├── chemistry/                     # 化学の単元別読み物
│   ├── biology/                       # 生物の単元別読み物
│   └── earth_science/                 # 地学の単元別読み物
├── quality/
│   ├── core_first_selection.md        # 最初の150枚の選定・順番監査
│   ├── coverage_matrix.csv            # 学年×領域×単元×種別の実数
│   ├── topic_audit.md                 # 表面だけによる直接想起トピック照合
│   ├── qa_report.md                   # 構造・重複・ルビ検査
│   └── SHA256SUMS.txt                 # ファイル整合性
└── sources/SOURCES.md                 # 公的基準・形式資料
```

## 目的別の最短経路

- **初めて学ぶ**：`anki/science_core_first_150.tsv`
- **全体をAnkiへ**：`anki/science_tagged.tsv` → `anki/IMPORT_GUIDE.md`
- **一つの表で確認**：`tables/all_cards_front_back.md`
- **順序立てて理解**：`reading/00_start_here/learning_plan.md` → `reading/02_grade_maps/` → 各領域の`README.md`
- **内容を編集**：`science_cards.xlsx` または `data/science_cards_master.csv`
- **図版の配置と検証を確認**：`assets/README.md`
- **抜け・重複を監査**：`quality/`
