from app import app, db
from sqlalchemy import text

app.app_context().push()

try:
    with db.engine.connect() as conn:
        # Add the updated_at column
        conn.execute(text('ALTER TABLE leave_policies ADD COLUMN updated_at DATETIME'))
        conn.commit()
        print("✅ updated_at column added successfully!")
        
        # Verify
        result = conn.execute(text('PRAGMA table_info(leave_policies)'))
        columns = result.fetchall()
        print("\nUpdated leave_policies table columns:")
        for col in columns:
            print(f"  {col}")
except Exception as e:
    print(f"Error: {e}")
