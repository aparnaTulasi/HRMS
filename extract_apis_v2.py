import os
import re

routes_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\routes"
leave_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\leave"

def extract_routes(directory):
    all_routes = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path_full = os.path.join(root, file)
                with open(path_full, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                    # 1. Standard @bp.route
                    pattern = r"@(\w+)\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?\)\s+def\s+(\w+)"
                    matches = re.findall(pattern, content)
                    for bp, route, methods, func in matches:
                        meth = methods.replace("'", "").replace('"', "") if methods else "GET"
                        all_routes.append({"file": file, "bp": bp, "route": route, "methods": meth, "func": func})
                    
                    # 2. Shorthand @bp.get, @bp.post, etc.
                    shorthand_pattern = r"@(\w+)\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]\)\s+def\s+(\w+)"
                    s_matches = re.findall(shorthand_pattern, content)
                    for bp, verb, route, func in s_matches:
                        all_routes.append({"file": file, "bp": bp, "route": route, "methods": verb.upper(), "func": func})
    return all_routes

all_routes = extract_routes(routes_dir) + extract_routes(leave_dir)

# Mapping Blueprints to Base URLs from app.py
bp_map = {
    "auth_bp": "/api/auth",
    "admin_bp": "/api/admin",
    "superadmin_bp": "/api/superadmin",
    "hr_bp": "/api/hr",
    "employee_bp": "/api",
    "attendance_bp": "/api/attendance",
    "documents_bp": "/api/documents",
    "payroll_bp": "/api",
    "user_bp": "/api/user",
    "policies_bp": "/api/policies",
    "leave_bp": "", # No prefix in app.py
    "approvals_bp": "/api/approvals",
    "company_bp": "/api/superadmin",
    "hr_docs_bp": "/api/hr-docs",
    "profile_bp": "", # No prefix
    "audit_bp": "",   # No prefix
    "support_bp": "/api/support",
    "calendar_bp": "/api/calendar",
    "shift_bp": "/api/shifts",
    "stabilization_bp": "/api/stabilization"
}

with open("all_apis_table.md", "w", encoding="utf-8") as f:
    f.write("# HRMS Full API list\n\n")
    f.write("| Module | Endpoint | Method | Function | File |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    
    unique_routes = []
    seen = set()
    for r in all_routes:
        base = bp_map.get(r['bp'], f"/api/{r['bp']}")
        full_path = f"{base}{r['route']}"
        entry = (full_path, r['methods'], r['func'])
        if entry not in seen:
            seen.add(entry)
            unique_routes.append({**r, "full_path": full_path})

    for r in sorted(unique_routes, key=lambda x: (x['file'], x['full_path'])):
        f.write(f"| {r['file']} | `{r['full_path']}` | {r['methods']} | `{r['func']}` | {r['file']} |\n")
