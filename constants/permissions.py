# Module Definitions
MODULES = [
    "Dashboard",
    "My Team",
    "Companies",
    "Departments",
    "Employees",
    "Attendance",
    "Requests",
    "Payroll",
    "Reports",
    "Administration",
    "Onboarding",
    "Recruitment",
    "Travel & Expenses",
    "Loan",
    "Financial Reports",
    "Documents",
    "Settings",
    "Role Management",
    "Audit Logs"
]

# Action Definitions
ACTIONS = ["VIEW", "CREATE", "EDIT", "DELETE", "EXPORT"]

# Permission Code Generator
def get_permission_code(module, action):
    """
    Standardizes permission codes like 'DASHBOARD_VIEW'
    """
    clean_module = module.upper().replace(" ", "_").replace("&", "AND")
    return f"{clean_module}_{action.upper()}"

# All Possible Permission Codes
ALL_PERMISSIONS = [get_permission_code(m, a) for m in MODULES for a in ACTIONS]
