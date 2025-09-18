import sqlite3

# ─── DBファイルパス ───
DB_PATH = "civitai_prompts.db"

# ─── category列がなければ追加 ───
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE prompts ADD COLUMN category TEXT")
except sqlite3.OperationalError:
    # すでに存在する場合は無視
    pass
conn.commit()
conn.close()

# ─── DB接続 ───
def connect_db():
    return sqlite3.connect(DB_PATH)

# ─── データ確認 ───
def show_prompts(limit=10):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, text, category FROM prompts LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        print(f"ID: {row[0]}, Category: {row[2]}\nPrompt: {row[1]}\n{'-'*50}")

# ─── カテゴリ更新 ───
def update_category(prompt_id, new_category):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE prompts SET category=? WHERE id=?", (new_category, prompt_id))
    conn.commit()
    conn.close()
    print(f"Prompt ID {prompt_id} のカテゴリを '{new_category}' に更新しました。")

# ─── キーワード検索 ───
def search_prompt(keyword):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, text, category FROM prompts WHERE text LIKE ?", (f"%{keyword}%",))
    rows = cur.fetchall()
    conn.close()
    if rows:
        for row in rows:
            print(f"ID: {row[0]}, Category: {row[2]}\nPrompt: {row[1]}\n{'-'*50}")
    else:
        print("該当するプロンプトはありません。")

# ─── 実行用メニュー ───
def menu():
    while True:
        print("\n1: データ確認")
        print("2: カテゴリ更新")
        print("3: キーワード検索")
        print("4: 終了")
        choice = input("選択: ").strip()
        if choice == "1":
            limit_input = input("表示件数 (デフォルト10): ").strip()
            limit = int(limit_input) if limit_input.isdigit() else 10
            show_prompts(limit)
        elif choice == "2":
            pid_input = input("更新するID: ").strip()
            if not pid_input.isdigit():
                print("IDは数字で入力してください。")
                continue
            pid = int(pid_input)
            cat = input("新しいカテゴリ: ").strip()
            update_category(pid, cat)
        elif choice == "3":
            kw = input("検索キーワード: ").strip()
            search_prompt(kw)
        elif choice == "4":
            break
        else:
            print("無効な選択です。")

# ─── メイン ───
if __name__ == "__main__":
    menu()

