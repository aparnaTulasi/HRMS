from models import db
from models.company import Company
from models.employee import Employee

def generate_employee_id(company_id):
    """
    Generates a new unique employee ID like 'COMPCODE-0001'.
    Consistent across Admin and SuperAdmin creation flows.
    """
    company = Company.query.get(company_id)
    prefix = (company.company_code if company and company.company_code else "EMP").upper()

    # Find the last employee for this company to determine the next number
    last_employee = db.session.query(Employee.id, Employee.employee_id).filter(
        Employee.company_id == company_id,
        Employee.employee_id.like(f"{prefix}-%")
    ).order_by(db.desc(Employee.id)).first()
    
    if last_employee and last_employee.employee_id:
        try:
            # Extract number from COMPCODE-0001
            last_num_str = last_employee.employee_id.split('-')[-1]
            last_num = int(last_num_str)
            next_num = last_num + 1
        except (ValueError, IndexError):
            # Fallback: count total employees
            next_num = Employee.query.filter_by(company_id=company_id).count() + 1
    else:
        # First employee for this company
        next_num = 1
        
    return f"{prefix}-{next_num:04d}"
