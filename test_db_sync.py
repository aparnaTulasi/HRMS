from app import app, db
import traceback

def test_sync():
    with app.app_context():
        try:
            print("Running db.create_all()...")
            db.create_all()
            print("✅ Success!")
        except Exception as e:
            print("❌ Failure!")
            print(traceback.format_exc())

if __name__ == "__main__":
    test_sync()
