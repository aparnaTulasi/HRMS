import sys
import traceback
try:
    from app import create_app
    from config import Config
    app = create_app(Config)
    print("SUCCESS: App loaded correctly")
except Exception as e:
    traceback.print_exc()
