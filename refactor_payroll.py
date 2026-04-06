import re
import os

FILE_PATH = "routes/payroll.py"

with open(FILE_PATH, "r") as f:
    lines = f.readlines()

new_lines = []
skip_decorator_def = False

for i, line in enumerate(lines):
    # Add imports early
    if "from utils.decorators import token_required" in line:
        new_lines.append(line.replace("token_required", "token_required, permission_required"))
        new_lines.append("from constants.permissions_registry import Permissions\n")
        continue
    
    # Remove definition of require_roles
    if line.startswith("def require_roles(*roles):"):
        skip_decorator_def = True
    
    if skip_decorator_def:
        if line.strip() == "return decorator":
            skip_decorator_def = False
            continue
        continue

    # Replace @require_roles usage
    if "@require_roles" in line:
        # Determine the preceding route to guess the permission
        # Look back up to 2 lines
        prev_line = new_lines[-1] if len(new_lines) > 0 else ""
        route_path = ""
        method = "get"
        m = re.search(r'@payroll_bp\.(get|post|put|delete|patch)\("([^"]+)"\)', prev_line)
        if m:
            method = m.group(1).lower()
            route_path = m.group(2)
        else:
            m2 = re.search(r'@payroll_bp\.route\("([^"]+)", \S+=\["(GET|POST|PUT|DELETE|PATCH)"\]\)', prev_line, re.IGNORECASE)
            if m2:
                route_path = m2.group(1)
                method = m2.group(2).lower()
        
        # Mapping rules
        if route_path == "":
            # fallback
            permission = "Permissions.PAYROLL_VIEW" 
        else:
            if "employee" in route_path and "/me" in route_path:
                permission = None # No permission needed to view own data, but actually we use PAYROLL_VIEW if we must, or just omit if it's personal.
                # Actually, in phase 5, employee personal actions don't use @require_roles. The existing code uses @require_roles("EMPLOYEE")
            
            # Identify the permission
            # Generates
            if "/generate" in route_path:
                permission = "Permissions.PAYROLL_GENERATE"
            elif "/action" in route_path:
                permission = "Permissions.PAYROLL_APPROVE"
            elif "employee" in route_path and "EMPLOYEE" in line:
                # Employee personal route, keep it or remove it entirely
                permission = "None"
            elif method == "get":
                permission = "Permissions.PAYROLL_VIEW"
            elif method == "post":
                permission = "Permissions.PAYROLL_CREATE"
            elif method in ["put", "patch", "delete"]:
                permission = "Permissions.PAYROLL_EDIT"
            else:
                permission = "Permissions.PAYROLL_VIEW"
        
        if permission == "None":
            # For employee personal routes, we can just remove the @require_roles decorator entirely
            # because personal routes rely on token_required which verifies identity.
            continue
        
        new_lines.append(f"@{permission.replace('Permissions.', 'permission_required(Permissions.')})\n")
    else:
        new_lines.append(line)

with open(FILE_PATH, "w") as f:
    f.writelines(new_lines)

print("Refactored routes/payroll.py")
