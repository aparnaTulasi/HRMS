from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash
from datetime import datetime
from models import db
from models.user import User
from models.company import Company
from utils.decorators import token_required, role_required
from models.employee import Employee
from utils.email_utils import send_account_created_alert, send_login_credentials
from utils.url_generator import build_web_address, build_common_login_url
from models.employee_onboarding_request import EmployeeOnboardingRequest

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{'id': emp.id, 'name': emp.full_name} for emp in employees])

@admin_bp.route('/create-hr', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def create_hr():
    print("🔵 Create HR Request Received...", flush=True)
    data = request.get_json(force=True)
    email = data.get('email') or data.get('company_email')
    personal_email = data.get('personal_email')
    if not email or not data.get('password'):
        return jsonify({'message': 'Email and Password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    hashed_password = generate_password_hash(data['password'])
    new_user = User(email=email, password=hashed_password, role='HR', company_id=g.user.company_id)
    db.session.add(new_user)
    db.session.flush()

    company = Company.query.get(g.user.company_id)
    emp_count = Employee.query.filter_by(company_id=g.user.company_id).count()
    emp_code = f"{company.company_code}-{emp_count + 1:04d}"

    new_employee = Employee(
        user_id=new_user.id,
        company_id=g.user.company_id,
        company_code=company.company_code,
        employee_id=emp_code,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        company_email=email,
        personal_email=personal_email,
        department=data.get('department', 'Human Resources'),
        designation=data.get('designation', 'HR Manager')
    )
    db.session.add(new_employee)
    db.session.commit()

    # --- Terminal Logging & Email Sending ---
    print(f"✅ HR Created: {email} | Personal Email: {personal_email}", flush=True)

    if personal_email:
        try:
            company = Company.query.get(g.user.company_id)
            creator_name = g.user.employee_profile.full_name if g.user.employee_profile else "Admin"
            web_address = build_web_address(company.subdomain)
            login_url = build_common_login_url(company.subdomain)
            
            send_account_created_alert(personal_email, company.company_name, creator_name)
            send_login_credentials(
                personal_email=personal_email,
                company_email=email,
                password=data['password'],
                company_name=company.company_name,
                web_address=web_address,
                login_url=login_url,
                created_by=creator_name
            )
            print(f"📧 Credentials sent to {personal_email}", flush=True)
        except Exception as e:
            print(f"❌ Failed to send email: {e}", flush=True)

    return jsonify({'message': 'HR created successfully'}), 201

@admin_bp.route('/employees', methods=['POST'])
@admin_bp.route('/create-employee', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR'])
def create_employee():
    print("🔵 Create Employee Request Received...", flush=True)
    data = request.get_json(force=True)
    
    email = data.get('email') or data.get('company_email')
    required = ['first_name', 'last_name', 'password', 'personal_email']
    if not email or not all(k in data for k in required):
        return jsonify({'message': 'Missing required fields'}), 400
        
    company_id = g.user.company_id
    email = email.lower().strip()
    personal_email = data['personal_email'].lower().strip()
    
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409
        
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        email=email,
        password=hashed_password,
        role=data.get('role', 'EMPLOYEE'),
        company_id=company_id,
        status='ACTIVE'
    )
    db.session.add(new_user)
    db.session.flush()
    
    company = Company.query.get(company_id)
    emp_count = Employee.query.filter_by(company_id=company_id).count()
    emp_code = f"{company.company_code}-{emp_count + 1:04d}"
    
    date_of_joining = data.get('date_of_joining')
    if date_of_joining:
        try:
            date_of_joining = datetime.strptime(date_of_joining, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    new_employee = Employee(
        user_id=new_user.id,
        company_id=company_id,
        company_code=company.company_code,
        employee_id=emp_code,
        first_name=data['first_name'],
        last_name=data['last_name'],
        company_email=email,
        personal_email=personal_email,
        department=data.get('department'),
        designation=data.get('designation'),
        date_of_joining=date_of_joining
    )
    db.session.add(new_employee)
    db.session.commit()
    
    print(f"✅ Employee Created: {email} | Personal Email: {personal_email}", flush=True)

    try:
        # Send Emails
        creator_name = g.user.employee_profile.full_name if g.user.employee_profile else "Admin"
        web_address = build_web_address(company.subdomain)
        login_url = build_common_login_url(company.subdomain)
        
        # Mail 1: Alert
        send_account_created_alert(personal_email, company.company_name, creator_name)
        
        # Mail 2: Credentials
        send_login_credentials(
            personal_email=personal_email,
            company_email=email,
            password=data['password'],
            company_name=company.company_name,
            web_address=web_address,
            login_url=login_url,
            created_by=creator_name
        )
        print(f"📧 Credentials sent to {personal_email}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send email: {e}", flush=True)
    
    return jsonify({'message': 'Employee created successfully'}), 201

@admin_bp.route('/onboarding-requests', methods=['GET'])
@token_required
@role_required(['ADMIN'])
def list_onboarding_requests():
    reqs = EmployeeOnboardingRequest.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{
        "id": r.id,
        "first_name": r.first_name,
        "last_name": r.last_name,
        "personal_email": r.personal_email,
        "department": r.department,
        "designation": r.designation,
        "date_of_joining": r.date_of_joining.isoformat() if r.date_of_joining else None,
        "status": r.status
    } for r in reqs])

@admin_bp.route('/onboarding-requests/<int:req_id>/approve', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def approve_onboarding_request(req_id):
    r = EmployeeOnboardingRequest.query.filter_by(id=req_id, company_id=g.user.company_id).first()
    if not r:
        return jsonify({"message": "Request not found"}), 404
    if r.status != "PENDING":
        return jsonify({"message": "Request already processed"}), 400

    r.status = "APPROVED"
    r.approved_by = g.user.id
    r.approved_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Request approved. Now create employee with /api/admin/employees"}), 200

@admin_bp.route('/employees/<int:emp_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN','HR'])
def update_employee(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    if not emp:
        return jsonify({"message":"Employee not found"}), 404

    data = request.get_json(force=True)
    allowed = [
        "first_name","last_name","gender","date_of_birth","father_or_husband_name","mother_name",
        "department","designation","salary","date_of_joining","work_phone","personal_mobile",
        "personal_email","company_email","work_mode","branch_id","aadhaar_number","pan_number"
    ]
    for k in allowed:
        if k in data:
            if k in ["date_of_birth", "date_of_joining"] and data[k]:
                try:
                    val = datetime.strptime(data[k], '%Y-%m-%d').date()
                    setattr(emp, k, val)
                except ValueError:
                    pass
            else:
                setattr(emp, k, data[k])
    db.session.commit()
    return jsonify({"message":"Employee updated"}), 200

@admin_bp.route('/employees/<int:emp_id>/education', methods=['POST'])
@token_required
@role_required(['ADMIN','HR'])
def save_education(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    if not emp: return jsonify({"message":"Employee not found"}), 404
    emp.education_details = request.get_json(force=True)
    db.session.commit()
    return jsonify({"message":"Education saved"}), 200

@admin_bp.route('/employees/<int:emp_id>/last-work', methods=['POST'])
@token_required
@role_required(['ADMIN','HR'])
def save_last_work(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    if not emp: return jsonify({"message":"Employee not found"}), 404
    emp.last_work_details = request.get_json(force=True)
    db.session.commit()
    return jsonify({"message":"Last work saved"}), 200

@admin_bp.route('/employees/<int:emp_id>/statutory', methods=['POST'])
@token_required
@role_required(['ADMIN','HR'])
def save_statutory(emp_id):
    emp = Employee.query.filter_by(id=emp_id, company_id=g.user.company_id).first()
    if not emp: return jsonify({"message":"Employee not found"}), 404
    emp.statutory_details = request.get_json(force=True)
    db.session.commit()
    return jsonify({"message":"Statutory saved"}), 200