import sqlite3
import os

PROJECT_DIR = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
db_path = os.path.join(PROJECT_DIR, "database", "repo", "store.db")

def run_query(query, params=(), fetch=False, DB_PATH = db_path):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    if fetch:
        rows = cur.fetchall()
        conn.close()
        return rows
    conn.commit()
    conn.close()
    return "✅ Done"