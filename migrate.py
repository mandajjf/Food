"""
新增 calories、protein 欄位到 reviews 資料表。
對現有資料不影響，可安全重複執行。

本機：
    python migrate.py

Render PostgreSQL：
    DATABASE_URL="postgres://..." python migrate.py
"""
from dotenv import load_dotenv
load_dotenv()

from app import app
from database import db


def add_column(conn, table, column, col_type):
    try:
        conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.commit()
        print(f"  ✅ 新增欄位：{table}.{column}")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate column" in msg or "already exists" in msg:
            print(f"  ⏭️  已存在，跳過：{table}.{column}")
        else:
            print(f"  ❌ 錯誤 {table}.{column}：{e}")


with app.app_context():
    with db.engine.connect() as conn:
        add_column(conn, "reviews", "calories", "FLOAT")
        add_column(conn, "reviews", "protein",  "FLOAT")

print("\n遷移完成！")
