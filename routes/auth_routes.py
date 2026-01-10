from flask import Blueprint, request, jsonify
from flask_login import login_user
from werkzeug.security import check_password_hash
from models.user import User
import jwt
import datetime
from config import Config

auth_routes_bp = Blueprint('auth_routes', __name__)

ROLE_URLS = {
    "SUPER_ADMIN": "/super/dashboard",
    "ADMIN": "/admin/dashboard",
    "HR": "/hr/dashboard",
    "EMPLOYEE": "/employee/dashboard"
}

@auth_routes_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    login_user(user)
    
    token = jwt.encode({
        'user_id': user.id,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, Config.SECRET_KEY, algorithm="HS256")

    return jsonify({
        "token": token,
        "role": user.role,
        "url": ROLE_URLS.get(user.role, "/"),
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    })