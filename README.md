# CivitAI Prompt Collector (Rebuild)

## 🎯 Purpose (目的)
- CivitAI からプロンプトを自動収集する
- 収集したプロンプトをカテゴリ別に整理する
  - Style / Lighting / Composition / Mood / Basic / Technical (+ NSFW)
- 収集データを API で提供し、外部アプリ（特に ComfyUI）で活用できるようにする

---

## 📐 Rules (ルール)
1. 重複を避ける（ID単位でユニークに管理する）
2. 無秩序にファイルを増やさず、役割ごとに整理する
   - 実行用コード → `src/`
   - 補助スクリプト → `scripts/`
   - 古いバージョン → `archive/`
3. 小さなステップで開発を進める
   - DB保存 → 分類 → API化 → ComfyUI連携 の順で進める
4. README の目的とルールから外れない

---

## 🗂️ Project Structure (初期構成)

civitai-prompt-collector-rebuild/
├─ README.md ← この設計メモ
├─ requirements.txt ← 依存関係リスト（最小限から開始）
└─ src/
└─ main.py ← 旧 v8 をベースにしたメインコード


※ `archive/` フォルダを作り、過去のコードを保管しておくと混乱防止になる

---

## 🚀 Development Steps (開発ステップ)

### Step 1. 最小動作
- `main.py` にて CivitAI API からデータを収集し
- SQLite DB に保存するところまで実装する
- 依存関係を整理して `requirements.txt` に書く

### Step 2. 分類機能
- 収集データをルールまたは ML によって 6カテゴリ (+NSFW) に分類する
- DB にカテゴリ列を追加

### Step 3. API 化
- FastAPI を使って REST API を提供
- 収集済みデータや分類結果を外部から取得できるようにする

### Step 4. ComfyUI 連携
- ComfyUI ノードとして組み込み、生成時にプロンプトを活用できるようにする

---

## ✅ Goal (最終目標)
- **CivitAI のプロンプトを体系的に収集・整理・提供する仕組み**
- **ComfyUI から直接利用できる環境**


開発ログ

ステップ１
✅ 最小動作としてまず入れるもの
以下がステップ1で「動く」ために最低限必要な機能です：

機能	内容
CivitAI API からプロンプトを取得	指定されたエンドポイントで一定数取得
SQLite DB の初期化	テーブルを作る（プロンプト、ID、取得日時など）
重複チェック	同じIDを既に DB に持っていたらスキップ
データ保存	プロンプト・ID・取得日時などを DB に保存

まずは「カテゴリ付け」「API公開」「外部連携」はあと。動く土台を作るのが優先。

いいですね、新リポジトリ確認しました。これを元に `civitai_collector_v8.py` を整理する方向で案を作ります。以下は「どう整理するか」「どのように main.py にしていくか」の提案です。必要なら一緒にコードもリファクタリングします。

---

## 🔍 現状把握（仮定）

`civitai_collector_v8.py` にはおそらくこれらの処理が含まれていると思われます：

* CivitAI API へのアクセス／プロンプト収集
* データのフィルタリング・クレンジング
* プロンプトのカテゴリ付け（ある程度）
* SQLite など DB への保存
* ロギング or エラー処理
* 設定（APIキー・取得数・カテゴリルールなど）

---

## 🛠 main.py 整理案

以下は `main.py` にリファクタリングして「最小動作」を達成するための構造案です。

```
src/
└ main.py
   ├─ config.py         ← 設定値（APIキー、エンドポイント、カテゴリ名、取得数など）
   ├─ collector.py      ← CivitAI API からの取得処理
   ├─ cleaner.py        ← データクレンジング・重複の除去
   ├─ db.py             ← DB 接続と基本的な保存処理
   ├─ categories.py     ← カテゴリ定義と分類ルール（最小限）
   └─ logger.py         ← ログ出力（optional 最初はプリントでも可）
```

`main.py` 本体は：

```python
from config import settings
from collector import fetch_prompts
from cleaner import clean_prompts
from db import init_db, save_prompts
from categories import categorize

def main():
    init_db(settings.db_path)
    raw = fetch_prompts(settings)
    cleaned = clean_prompts(raw)
    categorized = categorize(cleaned)
    save_prompts(categorized)
    print("Done.")

if __name__ == "__main__":
    main()
---

## 🔍 現状把握（仮定）

`civitai_collector_v8.py` にはおそらくこれらの処理が含まれていると思われます：

* CivitAI API へのアクセス／プロンプト収集
* データのフィルタリング・クレンジング
* プロンプトのカテゴリ付け（ある程度）
* SQLite など DB への保存
* ロギング or エラー処理
* 設定（APIキー・取得数・カテゴリルールなど）

---

## 🛠 main.py 整理案

以下は `main.py` にリファクタリングして「最小動作」を達成するための構造案です。

```
src/
└ main.py
   ├─ config.py         ← 設定値（APIキー、エンドポイント、カテゴリ名、取得数など）
   ├─ collector.py      ← CivitAI API からの取得処理
   ├─ cleaner.py        ← データクレンジング・重複の除去
   ├─ db.py             ← DB 接続と基本的な保存処理
   ├─ categories.py     ← カテゴリ定義と分類ルール（最小限）
   └─ logger.py         ← ログ出力（optional 最初はプリントでも可）
```

`main.py` 本体は：

```python
from config import settings
from collector import fetch_prompts
from cleaner import clean_prompts
from db import init_db, save_prompts
from categories import categorize

def main():
    init_db(settings.db_path)
    raw = fetch_prompts(settings)
    cleaned = clean_prompts(raw)
    categorized = categorize(cleaned)
    save_prompts(categorized)
    print("Done.")

if __name__ == "__main__":
    main()
```

---

## ✅ 最小動作としてまず入れるもの

以下がステップ1で「動く」ために最低限必要な機能です：

| 機能                     | 内容                       |
| ---------------------- | ------------------------ |
| CivitAI API からプロンプトを取得 | 指定されたエンドポイントで一定数取得       |
| SQLite DB の初期化         | テーブルを作る（プロンプト、ID、取得日時など） |
| 重複チェック                 | 同じIDを既に DB に持っていたらスキップ   |
| データ保存                  | プロンプト・ID・取得日時などを DB に保存  |

まずは「カテゴリ付け」「API公開」「外部連携」はあと。動く土台を作るのが優先。

---

## ⚙ 具体的整理ステップ

1. **ファイルの分割**

   * `civitai_collector_v8.py` から必要な関数・処理を抜き出して `collector.py`, `db.py` などに分ける
   * 依存関係があるところを整理：外部ライブラリ（requests 等）以外は可能な限り標準ライブラリ or 軽い依存に

2. **設定ファイル（config）**

   * API キーや URL、取得件数、DBのパスなどを `config.py` に集中
   * 環境変数を使いたいなら `.env` を読み込む方式も検討

3. **データモデルの設計**

   * DB スキーマ設計（どのテーブルにどのカラムを持たせるか）を簡潔にする
   * 例：`prompts` テーブルに `id (主キー)`, `prompt_text`, `collected_at`, `category (最初は null 可)` など

4. **重複排除ロジック**

   * ID をキーにチェック
   * 複数取得可能なページがあるならページネーションも考慮

5. **エラー処理 & ログ**

   * API失敗やタイムアウト、DB書き込み失敗に対して基本的な例外処理
   * ログは最初は print で十分 → 将来的にログファイル方式など

---

## 🧰 提案するリファクタリングロードマップ

| ステップ  | やること                                         |
| ----- | -------------------------------------------- |
| **A** | `main.py` の雛形を作る（上記構造）                       |
| **B** | `collector.py` を実装：CivitAI からの取得 + raw データ返却 |
| **C** | `db.py` を実装：DB 初期化 + 保存関数                    |
| **D** | `cleaner.py` の実装：重複除去・必要ないフィールドを捨てる等         |
| **E** | カテゴリ付けの簡易版を `categories.py` で実装（後で改良可能）      |
| **F** | テストで最小動作確認 → `requirements.txt` を更新          |

---

# 🚀 最適リファクタリング案

## 1-1. プロジェクト構成を固定する

まずはシンプルな形にします。

```
CivitAI-Prompt-Collector-Rebuild/
├─ README.md
├─ requirements.txt
└─ src/
   ├─ main.py         ← 実行の起点
   ├─ collector.py    ← API呼び出し & データ取得
   ├─ db.py           ← DB管理（初期化・保存）
   ├─ cleaner.py      ← データ整理（重複排除など）
   └─ config.py       ← 設定（API URL, DBパス, 取得件数など）
```

👉 これ以上増やさない。
👉 後で `categories.py` や `api_server.py` を追加するのはOKだけど、Step 1 ではこの形だけ。

---

## 1-2. 最小動作のゴール

* **CivitAI APIからデータを取得**
* **SQLiteに保存（重複は無視）**

カテゴリ分けやAPI公開は後回し。
「まず動く」を最優先。

---

## 1-3. 各ファイルの役割（初期版）

### main.py

### collector.py

### cleaner.py

### db.py


## 1-4. 開発ステップ

1. 上記の構成を新しいリポジトリにコピー
2. `pip install requests` → `requirements.txt` に `requests` を追記
3. `python src/main.py` を実行

   * APIに繋がり、DBに保存されれば ✅ 成功

---

## 1-5. その後の拡張

* **Step 2:** `categories.py` を追加 → 簡易ルールでカテゴリ列を付与
* **Step 3:** FastAPI を導入して `api_server.py` で REST API 化
* **Step 4:** ComfyUI 連携用にノード化

---

📌 つまり「今やること」は：

* この最小構成で `main.py` を動かして、まず DB にデータを落とす
