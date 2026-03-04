import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
# Import all models to ensure they are registered
from models.company import Company
from models.user import User
from models.employee import Employee
from models.employee_bank import EmployeeBankDetails
from models.employee_address import EmployeeAddress
from models.employee_documents import EmployeeDocuments

with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully at instance/hrms.db")