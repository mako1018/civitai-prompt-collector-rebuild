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

---
