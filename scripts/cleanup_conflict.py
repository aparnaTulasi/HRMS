import os

def remove_conflicting_file():
    file_path = os.path.join(os.getcwd(), 'routes.py')
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✅ Successfully removed conflicting file: {file_path}")
        except Exception as e:
            print(f"❌ Failed to remove file: {e}")
    else:
        print(f"ℹ️ File not found: {file_path}")

if __name__ == "__main__":
    remove_conflicting_file()