import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_prompts(prompts, db_path="civitai_prompts.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for p in prompts:
        try:
            cur.execute("INSERT INTO prompts (id, text) VALUES (?, ?)", (p["id"], p["text"]))
        except sqlite3.IntegrityError:
            continue  # 既にある場合はスキップ
    conn.commit()
    conn.close()
