import os
import re

routes_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\routes"
leave_dir = r"c:\Users\nagas\OneDrive\Desktop\HRMS-main\HRMS-main\leave"

def extract_routes(directory):
    all_routes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Match @bp.route('/path', methods=['GET']) def func_name():
                    pattern = r"@(\w+)\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?\)\s+def\s+(\w+)"
                    matches = re.findall(pattern, content)
                    if matches:
                        all_routes[file] = matches
    return all_routes

routes = extract_routes(routes_dir)
leave_routes = extract_routes(leave_dir)

with open("all_apis.txt", "w", encoding="utf-8") as f:
    f.write("# Routes Directory\n")
    for file, r_list in routes.items():
        f.write(f"\n## {file}\n")
        for bp, path, methods, func in r_list:
            meth = methods if methods else "'GET'"
            f.write(f"- {path} [{meth}] -> {func}\n")
    
    f.write("\n# Leave Directory\n")
    for file, r_list in leave_routes.items():
        f.write(f"\n## {file}\n")
        for bp, path, methods, func in r_list:
            meth = methods if methods else "'GET'"
            f.write(f"- {path} [{meth}] -> {func}\n")
