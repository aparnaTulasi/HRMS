from app import app, db
from models.user import User
from models.permission import UserPermission
from models.employee import Employee
from models.role import Role, RolePermission

def diagnose_user(name_search):
    with app.app_context():
        # 1. Find the employee
        emp = Employee.query.filter(Employee.full_name.like(f'%{name_search}%')).first()
        if not emp:
            print(f"No employee found matching '{name_search}'")
            return
            
        user = User.query.get(emp.user_id)
        if not user:
            print(f"No user found for employee {emp.full_name}")
            return
            
        print(f"--- Diagnosing User: {emp.full_name} ---")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        
        # 2. Check Direct Permissions
        direct_perms = [p.permission_code for p in user.permissions]
        print(f"Direct Permissions (UserPermission table): {direct_perms}")
        
        # 3. Check Role Permissions
        role_obj = Role.query.filter_by(name=user.role, company_id=user.company_id).first()
        role_perms = []
        if role_obj:
            role_perms = [rp.permission_code for rp in role_obj.permissions]
            print(f"Role Permissions (RolePermission table) for role '{user.role}': {role_perms}")
        else:
            print(f"Role '{user.role}' not found in Roles table for company {user.company_id}")
            
        # 4. Check Combined Permissions (what my fix should return)
        all_perms = user.get_all_permissions_matrix()
        print(f"Aggregated Permissions Matrix (returned to UI): {all_perms}")
        
        # 5. Check if 'MODULE_' permissions are present
        module_perms = [p for p in all_perms if p.startswith('MODULE_')]
        if module_perms:
            print(f"Module Grouping Permissions found: {module_perms}")
        else:
            print("No 'MODULE_' prefixed permissions found. (Sidebar might need these to show groups)")

if __name__ == "__main__":
    import sys
    name = "Sidebar"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    diagnose_user(name)
