import sys, os
sys.path.insert(0, os.path.abspath('.'))
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

commands = [
    "ALTER TABLE users ADD COLUMN username VARCHAR(100) NULL",
]

with engine.connect() as conn:
    for cmd in commands:
        try:
            conn.execute(text(cmd))
            conn.commit()
            print(f"✅ Done: {cmd}")
        except Exception as e:
            print(f"⚠️  Skipped (likely already exists): {e}")

print("Migration complete.")
