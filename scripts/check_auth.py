import os

path = os.path.join("routes", "auth.py")
if os.path.exists(path):
    print(f"✅ {path} exists.")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "auth_bp = Blueprint('auth', __name__)" in content:
             print("✅ auth_bp is defined correctly.")
        else:
             print("❌ auth_bp is MISSING in the file content.")
else:
    print(f"❌ {path} does not exist.")