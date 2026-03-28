from app import app
from models import db
from sqlalchemy import text

def update_squad_schema():
    with app.app_context():
        try:
            # Add department
            db.session.execute(text("ALTER TABLE squads ADD COLUMN department VARCHAR(100)"))
            print("Added column: department")
        except Exception as e:
            print(f"Column department might already exist: {e}")

        # Update squad_type default is not easy via SQL standard without dialect specific, 
        # but the model handles it on new inserts. Existing data might need update if needed.
        
        db.session.commit()
        print("Squad schema update completed.")

if __name__ == "__main__":
    update_squad_schema()
