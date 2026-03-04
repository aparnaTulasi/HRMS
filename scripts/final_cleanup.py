import os
import shutil

def comprehensive_cleanup():
    """
    Removes all obsolete files and directories from the old multi-tenant architecture,
    leaving only the files needed for the current single-database design.
    """
    # List of all files and directories that are no longer needed.
    obsolete_paths = [
        # Old root-level scripts
        "create_future_invo.py", "debug_user.py", "delete_user.py", "fix_db_schema.py", "reactivate_admin.py", "test_api.py",
        
        # Old models
        "models/master.py", "models/master_employee.py", "models/system_urls.py", "models/rbac.py",
        
        # Old utils directory
        "utils",
        
        # Old employee module files
        "employee/documents.py", "employee/employee_routes.py", "employee/check_companies.py",
        "employee/clear_master_db.py", "employee/fix_employee_schema.py", "employee/inspect_db.py",
        "employee/migrate_urls.py", "employee/view_data.py",
        
        # Old auth script
        "auth/fix_company_schema.py",
        
        # Old policies directory
        "policies",
        
        # Previous cleanup scripts
        "cleanup.py"
    ]

    print("🧹 Starting comprehensive cleanup...")

    # Remove all obsolete scripts except for init_db.py
    scripts_dir = "scripts"
    if os.path.exists(scripts_dir):
        for filename in os.listdir(scripts_dir):
            if filename != "init_db.py":
                obsolete_paths.append(os.path.join(scripts_dir, filename))

    for path in obsolete_paths:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"✅ Removed directory: {path}")
                else:
                    os.remove(path)
                    print(f"✅ Removed file: {path}")
            except Exception as e:
                print(f"❌ Error removing {path}: {e}")

    print("\n✨ Cleanup complete! Your project is now clean and uses the Single Database Architecture.")
    print("👉 You can now safely delete 'final_cleanup.py'.")

if __name__ == "__main__":
    comprehensive_cleanup()