# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models
from .user import User
from .super_admin import SuperAdmin
from .company import Company
from .employee import Employee
from .attendance import Attendance
from .permission import Permission, UserPermission
from .department import Department
from .employee_address import EmployeeAddress
from .employee_bank import EmployeeBankDetails
from .employee_documents import EmployeeDocument
from .urls import SystemURL
from .filter import FilterConfiguration
from .approvals import ApprovalRequest, ApprovalStep, ApprovalAction
from .payslip import Payslip
from .asset import Asset, AssetAllocation
from .travel_expense import TravelExpense
from .shift import Shift, ShiftAssignment
from .regularization import RegularizationRequest
from .payroll import SalaryComponent, SalaryStructure, SalaryStructureComponent, EmployeeSalaryStructure, PayrollRun, PayrollRunEmployee, PayrollEarning, PayrollDeduction, PayrollSummary