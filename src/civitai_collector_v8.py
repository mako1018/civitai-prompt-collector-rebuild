#!/usr/bin/env python3
# civitai_collector_v8.py
# V8: 汎用 CivitAI プロンプトコレクター
# - 複数モデル対応（ただし実行時は Illustrious Realism をデフォルトで収集）
# - 収集: API ページング、limit=100、max_items デフォルト 5000
# - 分類: キーワードベースでカテゴリ分類（NSFW 含む）
# - 可視化: モデルごとカテゴリ分布をスタック棒グラフで表示

import requests
import json
import sqlite3
import time
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import sys
import re
import os  # 追加

class CivitaiPromptCollector:
    def __init__(self, db_path="civitai_dataset.db", user_agent=None):
        self.base_url = "https://civitai.com/api/v1/images"
        self.db_path = db_path
        self.user_agent = user_agent or "CivitaiPromptCollector/1.0 (+https://example.com)"
        self.setup_database()

        # カテゴリ定義（必要に応じて語彙を追加してください）
        self.categories = {
            "realism_quality": ["realistic skin", "intricate details", "ultra-detailed", "photorealistic"],
            "lighting": ["cinematic lighting", "dynamic lighting", "soft lighting", "studio lighting", "dramatic lighting", "golden hour", "backlight", "rim light"],
            "composition": ["portrait", "full body", "close-up", "upper body", "headshot", "wide shot", "rule of thirds"],
            "character_features": ["detailed face", "expressive eyes", "facial features", "beautiful", "hands detail"],
            "technical": ["highres", "masterpiece", "best quality", "high resolution", "8k", "ultra high res"],
            "texture": ["skin texture", "hair detail", "fabric detail", "detailed texture", "rough texture"],
            "style": ["anime", "manga", "3d render", "oil painting", "watercolor", "digital art", "photorealism", "realistic"],
            "mood": ["melancholic", "cheerful", "mysterious", "elegant", "energetic", "moody", "dark"],
            "nsfw_safe": ["clothed", "sfw", "dress", "casual wear", "fully clothed", "covered"],
            "nsfw_suggestive": ["cleavage", "revealing clothing", "tight clothing", "suggestive pose", "see-through"],
            "nsfw_mature": ["lingerie", "underwear", "bikini", "swimsuit", "partial nudity", "braless"],
            "nsfw_explicit": ["nude", "naked", "nsfw", "explicit", "uncensored", "full nudity"]
        }

        # 単純化のため、キーワードマッチングは小文字で比較する
        self._prepare_keyword_patterns()

    def _prepare_keyword_patterns(self):
        """キーワードリストから正規表現パターンを作る（語順や小文字化に強くする）"""
        self.category_patterns = {}
        for cat, keywords in self.categories.items():
            # escape each keyword, match word boundaries when appropriate
            patterns = []
            for kw in keywords:
                kw_escaped = re.escape(kw.lower())
                # allow matching inside prompt text (simple contains); use word boundaries for single-word tokens
                patterns.append(re.compile(kw_escaped))
            self.category_patterns[cat] = patterns

    def setup_database(self):
        """SQLite データベースとテーブルを作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS civitai_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            civitai_id TEXT UNIQUE,
            full_prompt TEXT,
            negative_prompt TEXT,
            quality_score INTEGER,
            reaction_count INTEGER,
            comment_count INTEGER,
            download_count INTEGER,
            prompt_length INTEGER,
            tag_count INTEGER,
            model_name TEXT,
            model_id TEXT,
            collected_at TIMESTAMP,
            raw_metadata TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            category TEXT,
            keywords TEXT,
            confidence REAL,
            FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
        )
        ''')

        conn.commit()
        conn.close()

    def fetch_batch(self, url_or_params, max_retries=3):
        """APIから1ページ分を取得（nextPage/cursor対応、リトライ付き）"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        from .config import CIVITAI_API_ENV  # type: ignore
        api_key = os.getenv(CIVITAI_API_ENV)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # --- 追加: ヘッダー値を Latin-1 に安全化（置換）して問題箇所をログ出力 ---
        unsafe = []
        for k, v in list(headers.items()):
            if not isinstance(v, str):
                headers[k] = str(v)
                v = headers[k]
            try:
                v.encode("latin-1")
            except UnicodeEncodeError:
                unsafe.append(k)
                # 非Latin-1文字を '?' に置換して送信可能にする
                headers[k] = v.encode("latin-1", "replace").decode("latin-1")
        if unsafe:
            print(f"[fetch_batch] sanitized headers with non-latin1 characters: {unsafe}")
        # --- 追加終了 ---

        for attempt in range(1, max_retries + 1):
            try:
                if isinstance(url_or_params, dict):
                    response = requests.get(self.base_url, params=url_or_params, headers=headers, timeout=(5, 100))
                else:
                    response = requests.get(url_or_params, headers=headers, timeout=(5, 100))
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    next_page = data.get("metadata", {}).get("nextPage")
                    return items, next_page
                elif response.status_code == 429:
                    wait = 60
                    print(f"[fetch_batch] 429 Rate limited. Waiting {wait} seconds... (attempt {attempt}/{max_retries})")
                    time.sleep(wait)
                    continue
                else:
                    print(f"[fetch_batch] HTTP {response.status_code}: {response.text[:200]}")
                    return [], None
            except requests.exceptions.RequestException as e:
                print(f"[fetch_batch] Attempt {attempt} failed: {e}")
                time.sleep(3 * attempt)
                continue
        print("[fetch_batch] All retries failed for:", url_or_params)
        return [], None

    def extract_prompt_data(self, item):
        """API レスポンス項目から必要フィールドを抜き出す"""
        try:
            meta = item.get("meta", {}) or {}
            stats = item.get("stats", {}) or {}

            full_prompt = meta.get("prompt") or ""
            negative_prompt = meta.get("negativePrompt") or ""

            prompt_data = {
                "civitai_id": str(item.get("id", "")),
                "full_prompt": full_prompt,
                "negative_prompt": negative_prompt,
                "reaction_count": stats.get("reactionCount", 0),
                "comment_count": stats.get("commentCount", 0),
                "download_count": stats.get("downloadCount", 0),
                "model_name": meta.get("Model") or meta.get("model") or item.get("model") or "",
                "model_id": str(item.get("modelId") or meta.get("ModelId") or ""),
                "raw_metadata": json.dumps(item, ensure_ascii=False)
            }

            prompt_text = prompt_data["full_prompt"] or ""
            prompt_data["prompt_length"] = len(prompt_text)
            prompt_data["tag_count"] = len([t for t in [s.strip() for s in prompt_text.split(",")] if t])
            prompt_data["quality_score"] = self.calculate_quality_score(prompt_text, stats)

            return prompt_data
        except Exception as e:
            print("[extract_prompt_data] Error:", e)
            return None

    def calculate_quality_score(self, prompt, stats):
        """シンプルな品質スコア計算（キーワード＋リアクション）"""
        score = 0
        pl = (prompt or "").lower()

        technical_keywords = ["masterpiece", "best quality", "ultra-detailed", "highres", "high resolution", "8k"]
        score += sum(2 for kw in technical_keywords if kw in pl)

        detail_keywords = ["intricate", "detailed", "realistic", "sharp", "clear"]
        score += sum(1 for kw in detail_keywords if kw in pl)

        reactions = stats.get("reactionCount", 0)
        score += min(reactions // 5, 20)

        word_count = len((prompt or "").split())
        if 15 <= word_count <= 80:
            score += 3

        return score

    def categorize_prompt(self, prompt_text):
        """キーワードマッチベースのカテゴリ分け。返却: {category: {keywords: [...], confidence: float}}"""
        categories_found = {}
        text = (prompt_text or "").lower()

        # キーワードのパターンでマッチを探す
        for category, patterns in self.category_patterns.items():
            found = []
            for pat in patterns:
                if pat.search(text):
                    # マッチした語句を取り出（pattern.pattern から人間用に加工）
                    found.append(pat.pattern)
            if found:
                # 簡易 confidence = マッチ語数 / 定義語数
                confidence = float(len(found)) / max(1, len(self.categories.get(category, [])))
                categories_found[category] = {"keywords": found, "confidence": confidence}

        # NSFW 系が一切見つからなければ safe と仮定
        if not any(k.startswith("nsfw_") for k in categories_found.keys()):
            categories_found.setdefault("nsfw_safe", {"keywords": ["default_safe"], "confidence": 0.5})

        return categories_found

    def save_prompt_data(self, prompt_data):
        """DB に保存。既存の civitai_id があれば更新して prompt_id を返す"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # UPSERT 相当の処理: 既存なら更新、存在しなければ挿入
            cursor.execute('''
            INSERT INTO civitai_prompts
            (civitai_id, full_prompt, negative_prompt, quality_score,
             reaction_count, comment_count, download_count, prompt_length, tag_count,
             model_name, model_id, collected_at, raw_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(civitai_id) DO UPDATE SET
                full_prompt=excluded.full_prompt,
                negative_prompt=excluded.negative_prompt,
                quality_score=excluded.quality_score,
                reaction_count=excluded.reaction_count,
                comment_count=excluded.comment_count,
                download_count=excluded.download_count,
                prompt_length=excluded.prompt_length,
                tag_count=excluded.tag_count,
                model_name=excluded.model_name,
                model_id=excluded.model_id,
                collected_at=excluded.collected_at,
                raw_metadata=excluded.raw_metadata
            ''', (
                prompt_data["civitai_id"],
                prompt_data["full_prompt"],
                prompt_data["negative_prompt"],
                prompt_data["quality_score"],
                prompt_data["reaction_count"],
                prompt_data["comment_count"],
                prompt_data["download_count"],
                prompt_data["prompt_length"],
                prompt_data["tag_count"],
                prompt_data["model_name"],
                prompt_data["model_id"],
                datetime.now().isoformat(),
                prompt_data["raw_metadata"]
            ))
            conn.commit()

            # prompt_id を取得
            cursor.execute('SELECT id FROM civitai_prompts WHERE civitai_id = ?', (prompt_data["civitai_id"],))
            row = cursor.fetchone()
            prompt_id = row[0] if row else None

            # 既存のカテゴリを一旦削除してから新規挿入（重複防止）
            if prompt_id:
                cursor.execute('DELETE FROM prompt_categories WHERE prompt_id = ?', (prompt_id,))
                categories = self.categorize_prompt(prompt_data["full_prompt"])
                for category, data in categories.items():
                    cursor.execute('''
                    INSERT INTO prompt_categories (prompt_id, category, keywords, confidence)
                    VALUES (?, ?, ?, ?)
                    ''', (
                        prompt_id,
                        category,
                        json.dumps(data["keywords"], ensure_ascii=False),
                        data["confidence"]
                    ))
                conn.commit()
            return True
        except Exception as e:
            print("[save_prompt_data] Database error:", e)
            return False
        finally:
            conn.close()

    def collect_dataset(self, model_id=None, model_name=None, max_items=5000):
        """1モデル分（もしくは全体）の収集。model_id を None にすると modelId フィルタ無しで取得
        nextPage/cursorベースでページング対応
        """
        print(f"\n=== Collecting: {model_name or 'ALL_MODELS'} (model_id={model_id}) ===")
        collected = 0
        saved = 0
        params = {"limit": 20, "sort": "Most Reactions"}
        # デバッグ: APIパラメータ
        print(f"[collect_dataset] API params: {params}")
        if model_id:
            params["modelVersionId"] = model_id
            print(f"[collect_dataset] modelVersionId set: {model_id}")

        next_page_url = None
        page_count = 1
        while collected < max_items:
            if next_page_url:
                print(f"[collect_dataset] Fetching nextPage (collected: {collected}/{max_items})")
                batch, next_page_url = self.fetch_batch(next_page_url)
            else:
                print(f"[collect_dataset] Fetching page {page_count} (collected: {collected}/{max_items})")
                batch, next_page_url = self.fetch_batch(params)
            # デバッグ: APIレスポンス件数
            print(f"[collect_dataset] API batch items: {len(batch)}")
            if not batch:
                print("[collect_dataset] No more items returned by API for this page/params.")
                break
            for item in batch:
                if collected >= max_items:
                    break
                prompt_data = self.extract_prompt_data(item)
                if prompt_data:
                    if model_name and not prompt_data.get("model_name"):
                        prompt_data["model_name"] = model_name
                    if model_id and not prompt_data.get("model_id"):
                        prompt_data["model_id"] = str(model_id)
                    if prompt_data.get("full_prompt"):
                        ok = self.save_prompt_data(prompt_data)
                        if ok:
                            saved += 1
                collected += 1
            page_count += 1
            time.sleep(1.2)
            if not next_page_url:
                break
        print(f"[collect_dataset] Completed: saved {saved}/{collected} items for model '{model_name or model_id}'")
        return {"collected": collected, "saved": saved}

    def collect_for_models(self, models: dict, max_per_model=5000):
        """複数モデルを順に収集するユーティリティ
           models: {"Model Name": "modelId", ...}
        """
        results = {}
        for name, mid in models.items():
            res = self.collect_dataset(model_id=mid, model_name=name, max_items=max_per_model)
            results[name] = res
            # モデル間に短い待機を入れてAPI負荷を下げる
            time.sleep(2)
        return results

    def visualize_category_distribution(self, models_to_plot=None, normalize_percent=True, show=True, save_path=None):
        """
        DB から model_name × category の出現数を集計しスタック棒グラフ表示
        - models_to_plot: None -> DB 内の全モデル。リストを渡すとその順で表示。
        - normalize_percent: True のとき各モデルを 100% 正規化して割合表示
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT p.model_name, c.category, COUNT(*) as cnt
        FROM civitai_prompts p
        JOIN prompt_categories c ON p.id = c.prompt_id
        GROUP BY p.model_name, c.category
        ''')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("[visualize] No category data found in DB. Run collection first.")
            return

        data = defaultdict(lambda: defaultdict(int))
        models_set = set()
        categories_set = set()
        for model_name, category, cnt in rows:
            model_name = model_name or "Unknown"
            data[model_name][category] += cnt
            models_set.add(model_name)
            categories_set.add(category)

        # 選択モデル順
        if models_to_plot:
            model_names = [m for m in models_to_plot if m in data]
        else:
            model_names = sorted(models_set)

        if not model_names:
            print("[visualize] No matching models found to plot.")
            return

        categories = sorted(categories_set)
        # build matrix values[cat][model_index]
        matrix = np.zeros((len(categories), len(model_names)), dtype=float)
        for j, m in enumerate(model_names):
            total = sum(data[m].values()) or 1
            for i, cat in enumerate(categories):
                v = data[m].get(cat, 0)
                matrix[i, j] = (v / total) * 100.0 if normalize_percent else v

        # Plot stacked bar chart
        x = np.arange(len(model_names))
        bottom = np.zeros(len(model_names))

        # Color map: auto generate
        cmap = plt.get_cmap("tab20")
        num_colors = max(3, len(categories))
        colors = [cmap(i % 20) for i in range(num_colors)]

        plt.figure(figsize=(max(8, len(model_names)*1.4), 6))
        for i, cat in enumerate(categories):
            vals = matrix[i, :]
            plt.bar(x, vals, bottom=bottom, label=cat, color=colors[i % len(colors)])
            bottom += vals

        plt.xticks(x, model_names, rotation=25, ha='right')
        plt.ylabel("Category Distribution (%)" if normalize_percent else "Count")
        plt.title("Prompt Category Distribution by Model")
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=200)
            print(f"[visualize] Saved figure to: {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

# -----------------------
# 実行部分
# -----------------------
def main():
    # デフォルトは Illustrious Realism のみ（model_id=2091367）
    target_models = {
        "Realism Illustrious By Stable Yogi (ver.2091367)": "2091367"
    }

    collector = CivitaiPromptCollector(db_path="civitai_dataset.db")

    # 少量で動作確認するデフォルト値（本番では増やす）
    max_items_per_model = 10
    print("Starting collection for models:", list(target_models.keys()))
    results = collector.collect_for_models(target_models, max_per_model=max_items_per_model)
    print("Collection results:", results)

    # 可視化はデフォルトで非表示（CIやヘッドレス環境対策）
    collector.visualize_category_distribution(models_to_plot=list(target_models.keys()), normalize_percent=True, show=False)

    # テスト用コレクション（model_id=None で全モデル対象）
    print("\n=== TEST COLLECTION (all models) ===")
    c = CivitaiPromptCollector(db_path="test_collect.db")
    print(c.collect_for_models({"test": None}, max_per_model=1))

if __name__ == "__main__":
    main()
