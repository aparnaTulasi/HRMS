import sys, os
sys.path.insert(0, os.path.abspath('.'))
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

with engine.connect() as conn:
    # Disable FK checks for clean truncate
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    # Get all tables
    result = conn.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result.fetchall()]
    print(f"Found {len(tables)} tables: {tables}")

    for table in tables:
        try:
            conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            print(f"  ✅ Cleared: {table}")
        except Exception as e:
            print(f"  ⚠️  Skipped {table}: {e}")

    # Re-enable FK checks
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    conn.commit()

print("\n✅ All tables cleared. Database is now empty.")
print("   Re-create super admin via signup or seed script.")
