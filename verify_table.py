from app import app, db
from sqlalchemy import text

app.app_context().push()

try:
    with db.engine.connect() as conn:
        # Add the effective_to column
        conn.execute(text('ALTER TABLE leave_policies ADD COLUMN effective_to DATE'))
        conn.commit()
        print("✅ effective_to column added successfully!")
        
        # Verify
        result = conn.execute(text('PRAGMA table_info(leave_policies)'))
        columns = result.fetchall()
        print("\nUpdated leave_policies table columns:")
        for col in columns:
            print(f"  {col}")
except Exception as e:
    print(f"Error: {e}")
