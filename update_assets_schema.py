from app import app, db
from sqlalchemy import text

def update_assets_table():
    print("🔄 Updating 'assets' table schema...")
    with app.app_context():
        with db.engine.connect() as conn:
            # List of columns to add based on your Asset model
            # Format: (column_name, sql_type)
            new_columns = [
                ("serial_number", "TEXT"),
                ("brand", "TEXT"),
                ("model", "TEXT"),
                ("vendor_name", "TEXT"),
                ("purchase_date", "DATE"),
                ("purchase_cost", "FLOAT"),
                ("warranty_end_date", "DATE"),
                ("location", "TEXT"),
                ("notes", "TEXT"),
                ("is_active", "BOOLEAN DEFAULT 1"),
                ("created_at", "DATETIME"),
                ("updated_at", "DATETIME")
            ]

            for col_name, col_type in new_columns:
                try:
                    # SQLite syntax to add a column
                    conn.execute(text(f'ALTER TABLE assets ADD COLUMN {col_name} {col_type}'))
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    # Ignore error if column already exists
                    if "duplicate column name" in str(e).lower():
                        print(f"ℹ️  Column '{col_name}' already exists.")
                    else:
                        print(f"❌ Error adding '{col_name}': {e}")

            conn.commit()
            print("\n✨ 'assets' table updated successfully!")

def update_asset_allocations_table():
    print("\n🔄 Updating 'asset_allocations' table schema...")
    with app.app_context():
        with db.engine.connect() as conn:
            new_columns = [
                ("expected_return_date", "DATE"),
                ("return_date", "DATE"),
                ("issue_notes", "TEXT"),
                ("return_notes", "TEXT"),
                ("issued_by", "INTEGER"),
                ("returned_by", "INTEGER"),
                ("status", "TEXT DEFAULT 'Assigned'")
            ]
            for col_name, col_type in new_columns:
                try:
                    conn.execute(text(f'ALTER TABLE asset_allocations ADD COLUMN {col_name} {col_type}'))
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"ℹ️  Column '{col_name}' already exists.")
                    else:
                        print(f"❌ Error adding '{col_name}' to 'asset_allocations': {e}")
            conn.commit()
            print("\n✨ 'asset_allocations' table updated successfully!")

def update_asset_condition_logs_table():
    print("\n🔄 Updating 'asset_condition_logs' table schema...")
    with app.app_context():
        with db.engine.connect() as conn:
            new_columns = [
                ("log_type", "TEXT"),
                ("condition", "TEXT"),
                ("notes", "TEXT"),
                ("logged_by", "INTEGER"),
                ("logged_at", "DATETIME")
            ]
            for col_name, col_type in new_columns:
                try:
                    conn.execute(text(f'ALTER TABLE asset_condition_logs ADD COLUMN {col_name} {col_type}'))
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"ℹ️  Column '{col_name}' already exists.")
                    else:
                        print(f"❌ Error adding '{col_name}' to 'asset_condition_logs': {e}")
            conn.commit()
            print("\n✨ 'asset_condition_logs' table updated successfully!")

if __name__ == "__main__":
    update_assets_table()
    update_asset_allocations_table()
    update_asset_condition_logs_table()