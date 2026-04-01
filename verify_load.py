import sys
try:
    from app import create_app
    from config import Config
    app = create_app(Config)
    print("SUCCESS")
except ImportError as e:
    print(f"IMPORT_ERROR: {e}")
except Exception as e:
    print(f"OTHER_ERROR: {e}")
