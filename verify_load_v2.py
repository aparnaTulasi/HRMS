import sys
import traceback
import os

print(f"Python path: {sys.path}")
print(f"Current Dir: {os.getcwd()}")

try:
    print("Attempting to import superadmin_bp from routes.superadmin...")
    from routes.superadmin import superadmin_bp
    print("SUCCESS: superadmin_bp imported")
    
    print("Checking if parse_date is in routes.superadmin...")
    import routes.superadmin
    if hasattr(routes.superadmin, 'parse_date'):
        print("SUCCESS: parse_date found in routes.superadmin")
    else:
        print("FAILURE: parse_date NOT found in routes.superadmin")
        print(f"Attributes in routes.superadmin: {dir(routes.superadmin)}")

except ImportError:
    print("CAUGHT IMPORT ERROR:")
    traceback.print_exc()
except Exception as e:
    print(f"CAUGHT OTHER ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
