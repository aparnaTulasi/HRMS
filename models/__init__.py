# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models
from .user import User
from .company import Company
from .employee import Employee
from .attendance import Attendance
from .permission import Permission
from .department import Department
from .employee_address import EmployeeAddress
from .employee_bank import EmployeeBankDetails
from .employee_documents import EmployeeDocument