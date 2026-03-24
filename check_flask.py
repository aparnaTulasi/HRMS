try:
    from flask import current_app
    print("Flask import successful")
except ImportError as e:
    print(f"Flask import failed: {e}")
