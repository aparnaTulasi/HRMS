import os

files_to_delete = [
    os.path.join("scripts", "models.py"),
    os.path.join("scripts", "routes.py"),
]

for file_path in files_to_delete:
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✅ Deleted conflicting file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting {file_path}: {e}")
    else:
        print(f"ℹ️ File not found (already clean): {file_path}")