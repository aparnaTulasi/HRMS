from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from models import db
from models.user import User
from models.employee import Employee
from utils.decorators import token_required, role_required
from utils.email_utils import send_login_credentials
from utils.url_generator import build_web_host

admin_bp = Blueprint('admin', __name__)

def _parse_date(date_str: str):
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()

@admin_bp.route('/employees', methods=['GET'])
@token_required
@role_required(['ADMIN', 'HR'])
def get_employees():
    employees = Employee.query.filter_by(company_id=g.user.company_id).all()
    return jsonify([{
        'id': emp.id,
        'user_id': emp.user_id,
        'name': f"{emp.first_name} {emp.last_name}",
        'designation': emp.designation
    } for emp in employees])

@admin_bp.route('/employees', methods=['POST'])
@token_required
@role_required(["ADMIN", "HR"])
def create_employee():
    req_data = request.get_json(force=True)
    is_bulk = isinstance(req_data, list)
    data_list = req_data if is_bulk else [req_data]

    results = []
    company = g.user.company

    for data in data_list:
        try:
            email = (data.get("email") or "").strip().lower()
            password = (data.get("password") or "").strip()

            if not email or not password:
                results.append(({"email": email, "message": "email and password are required"}, 400))
                continue

            if User.query.filter_by(email=email).first():
                results.append(({"email": email, "message": "User with this email already exists"}, 409))
                continue

            role = (data.get("role") or "EMPLOYEE").strip().upper()
            if role in ["SUPER_ADMIN", "ADMIN"]:
                results.append(({"email": email, "message": f"Cannot create role: {role}"}, 403))
                continue

            hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

            new_user = User(
                email=email,
                password=hashed_password,
                role=role,  # EMPLOYEE default
                company_id=g.user.company_id,
                is_active=True
            )
            db.session.add(new_user)
            db.session.flush()

            doj = None
            if data.get("date_of_joining"):
                try:
                    doj = _parse_date(data.get("date_of_joining"))
                except ValueError:
                    db.session.rollback()
                    results.append(({"email": email, "message": "Invalid date format. Use YYYY-MM-DD"}, 400))
                    continue

            new_emp = Employee(
                user_id=new_user.id,
                company_id=g.user.company_id,
                first_name=data.get("first_name", "Employee"),
                last_name=data.get("last_name", "User"),
                department=data.get("department"),
                designation=data.get("designation", role),
                date_of_joining=doj
            )
            db.session.add(new_emp)
            db.session.commit()

            creator_host = build_web_host(g.user.email, company)
            created_by = g.user.role.replace("_", " ").title()
            email_sent = send_login_credentials(email, password, creator_host, created_by)

            results.append(({
                "email": email,
                "message": f"{role} created",
                "email_sent": email_sent
            }, 201))

        except IntegrityError as e:
            db.session.rollback()
            results.append(({"email": data.get("email"), "message": "DB integrity error", "error": str(e)}, 400))

        except Exception as e:
            db.session.rollback()
            results.append(({"email": data.get("email"), "message": "Server error", "error": str(e)}, 500))

    if not is_bulk:
        return jsonify(results[0][0]), results[0][1]

    # For bulk, return list of response bodies
    return jsonify([r[0] for r in results]), 207

@admin_bp.route('/hr', methods=['POST'])
@token_required
@role_required(["ADMIN"])
def create_hr():
    req_data = request.get_json(force=True)
    is_bulk = isinstance(req_data, list)
    data_list = req_data if is_bulk else [req_data]

    results = []
    company = g.user.company  # assuming relationship exists

    for data in data_list:
        try:
            email = (data.get("email") or "").strip().lower()
            password = (data.get("password") or "").strip()

            if not email or not password:
                results.append(({"email": email, "message": "email and password are required"}, 400))
                continue

            if User.query.filter_by(email=email).first():
                results.append(({"email": email, "message": "User with this email already exists"}, 409))
                continue

            # Create HR User
            hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
            new_user = User(
                email=email,
                password=hashed_password,
                role="HR",
                company_id=g.user.company_id,
                is_active=True
            )
            db.session.add(new_user)
            db.session.flush()

            # Create Employee profile for HR
            doj = None
            if data.get("date_of_joining"):
                try:
                    doj = _parse_date(data.get("date_of_joining"))
                except ValueError:
                    db.session.rollback()
                    results.append(({"email": email, "message": "Invalid date format. Use YYYY-MM-DD"}, 400))
                    continue

            new_emp = Employee(
                user_id=new_user.id,
                company_id=g.user.company_id,
                first_name=data.get("first_name", "HR"),
                last_name=data.get("last_name", "User"),
                department=data.get("department", "Human Resources"),
                designation=data.get("designation", "HR"),
                date_of_joining=doj
            )
            db.session.add(new_emp)
            db.session.commit()

            creator_host = build_web_host(g.user.email, company)
            email_sent = send_login_credentials(email, password, creator_host, "Admin")

            results.append(({
                "email": email,
                "message": "HR created",
                "email_sent": email_sent,
            }, 201))

        except IntegrityError as e:
            db.session.rollback()
            results.append(({"email": data.get("email"), "message": "DB integrity error", "error": str(e)}, 400))

        except Exception as e:
            db.session.rollback()
            results.append(({"email": data.get("email"), "message": "Server error", "error": str(e)}, 500))

    if not is_bulk:
        return jsonify(results[0][0]), results[0][1]

    # For bulk, return list of response bodies
    return jsonify([r[0] for r in results]), 207

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['ADMIN'])
def update_user(user_id):
    user = User.query.get(user_id)
    if not user or user.company_id != g.user.company_id:
        return jsonify({'message': 'User not found or unauthorized'}), 404
        
    data = request.get_json(force=True)
    
    # Update User fields
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    # Update Employee fields
    emp = Employee.query.filter_by(user_id=user.id).first()
    if emp:
        if 'first_name' in data: emp.first_name = data['first_name']
        if 'last_name' in data: emp.last_name = data['last_name']
        if 'department' in data: emp.department = data['department']
        if 'designation' in data: emp.designation = data['designation']
        
    db.session.commit()
    return jsonify({'message': 'User updated successfully'})

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user or user.company_id != g.user.company_id:
        return jsonify({'message': 'User not found or unauthorized'}), 404
    
    if user.id == g.user.id:
        return jsonify({'message': 'Cannot delete yourself'}), 400

    # Delete associated employee record
    Employee.query.filter_by(user_id=user.id).delete()
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'})