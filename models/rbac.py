# c:\Users\DELL5410\Desktop\HRMS\models\rbac.py
from enum import Enum

class Role(Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    HR_MANAGER = "HR_MANAGER"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    ACCOUNTS = "ACCOUNTS"

class Permission(Enum):
    CREATE_EMPLOYEE = "CREATE_EMPLOYEE"
    UPDATE_EMPLOYEE = "UPDATE_EMPLOYEE"
    DELETE_EMPLOYEE = "DELETE_EMPLOYEE"
    VIEW_ALL_EMPLOYEES = "VIEW_ALL_EMPLOYEES"
    APPROVE_USER = "APPROVE_USER"

class RBAC:
    @staticmethod
    def get_all_permissions(role):
        permissions = {
            Role.SUPER_ADMIN: [p for p in Permission],
            Role.ADMIN: [p for p in Permission],
            Role.HR_MANAGER: [
                Permission.CREATE_EMPLOYEE,
                Permission.UPDATE_EMPLOYEE,
                Permission.DELETE_EMPLOYEE,
                Permission.VIEW_ALL_EMPLOYEES,
                Permission.APPROVE_USER
            ],
            Role.MANAGER: [
                Permission.VIEW_ALL_EMPLOYEES
            ],
            Role.EMPLOYEE: [],
            Role.ACCOUNTS: []
        }
        return permissions.get(role, [])

    @staticmethod
    def can_access_employee(user_role, user_company_id, target_company_id, user_id=None, target_id=None):
        if user_role == Role.SUPER_ADMIN:
            return True
        
        if user_company_id != target_company_id:
            return False
            
        if user_role in [Role.ADMIN, Role.HR_MANAGER]:
            return True
            
        if user_role == Role.EMPLOYEE:
            return user_id == target_id
            
        return False
