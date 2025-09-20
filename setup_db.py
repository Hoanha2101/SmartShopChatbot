import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

schema_path = os.path.join(BASE_DIR, "database", "repo", "schema.sql")
db_path = os.path.join(BASE_DIR, "database", "repo", "store.db")

# Nếu file DB đã tồn tại thì xóa đi để tạo lại
if os.path.exists(db_path):
    os.remove(db_path)
    print("⚠️ Database cũ đã được xóa!")

# Tạo DB mới
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Đọc file schema.sql và chạy script
with open(schema_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

cursor.executescript(schema_sql)

conn.commit()
conn.close()

print("✅ Database mới đã được khởi tạo thành công!")
