from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user
import jwt
import datetime
import secrets
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 409

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password, role=data.get('role', 'EMPLOYEE'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check password
        if not check_password_hash(user.password, password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Determine user role and redirect URL
        if user.is_superadmin:
            role = 'SUPERADMIN'
            redirect_url = '/superadmin/dashboard'
        elif user.is_admin:
            role = 'ADMIN'
            redirect_url = '/admin/dashboard'
        elif user.is_hr:
            role = 'HR'
            redirect_url = '/hr/dashboard'
        else:
            role = 'EMPLOYEE'
            redirect_url = '/employee/dashboard'
        
        # Create JWT token
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, Config.SECRET_KEY, algorithm='HS256')
        
        # Login user for session management
        login_user(user)
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'role': role
            },
            'url': redirect_url,
            'role': role,
            'message': 'Login successful'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500