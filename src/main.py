from collector import fetch_prompts
from cleaner import clean_prompts
from db import init_db, save_prompts
from config import settings

def main():
    init_db(settings["DB_PATH"])
    raw = fetch_prompts(limit=settings["FETCH_LIMIT"])
    cleaned = clean_prompts(raw)
    save_prompts(cleaned)
    print("✅ Done.")

if __name__ == "__main__":
    main()
