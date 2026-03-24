import os
import re

routes_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\routes"
leave_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\leave"

def extract_routes(directory):
    all_routes = []
    # Flexible regex to handle multi-line decorators and optional methods
    # Matches @bp.route("/path", ...) def func():
    route_pattern = re.compile(r"@(\w+)\.route\(\s*['\"]([^'\"]+)['\"](?:.*methods=\[([^\]]+)\])?.*?\)\s+(?:@[^\n]+\n\s*)*def\s+(\w+)", re.DOTALL)
    shorthand_pattern = re.compile(r"@(\w+)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"].*?\)\s+(?:@[^\n]+\n\s*)*def\s+(\w+)", re.DOTALL)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path_full = os.path.join(root, file)
                with open(path_full, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                    # 1. Standard @bp.route
                    for match in route_pattern.finditer(content):
                        bp, route, methods, func = match.groups()
                        meth = methods.replace("'", "").replace('"', "").replace(" ", "") if methods else "GET"
                        all_routes.append({"file": file, "bp": bp, "route": route, "methods": meth, "func": func})
                    
                    # 2. Shorthand @bp.get, etc.
                    for match in shorthand_pattern.finditer(content):
                        bp, verb, route, func = match.groups()
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
    "leave_bp": "", 
    "approvals_bp": "/api/approvals",
    "company_bp": "/api/superadmin",
    "hr_docs_bp": "/api/hr-docs",
    "profile_bp": "",
    "audit_bp": "",
    "support_bp": "/api/support",
    "calendar_bp": "/api/calendar",
    "shift_bp": "/api/shifts",
    "stabilization_bp": "/api/stabilization",
    "attendance": "/api/attendance", # Added fallback
    "payroll": "/api",
    "employee": "/api",
    "user": "/api/user",
    "auth": "/api/auth"
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

print(f"Extraction complete. Found {len(unique_routes)} unique endpoints.")
