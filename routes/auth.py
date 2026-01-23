from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import jwt
from zoneinfo import ZoneInfo
from models import db
from models.super_admin import SuperAdmin
from models.user import User
from models.company import Company
from models.employee import Employee
from utils.email_utils import send_signup_otp, send_reset_otp
from utils.notification_utils import send_security_alert_email, send_login_success_email

auth_bp = Blueprint("auth", __name__)
JWT_SECRET = "superadmin-secret-key"

# -----------------------------
# 1️⃣ SIGNUP
# -----------------------------
@auth_bp.route("/super-admin/signup", methods=["POST"])
def super_admin_signup():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "Invalid JSON or Content-Type not set to application/json"}), 400

        email = data.get("email", "").lower().strip()
        password = data.get("password")
        confirm = data.get("confirm_password")

        if not email or not password or not confirm:
            return jsonify({"message": "All fields required"}), 400

        if password != confirm:
            return jsonify({"message": "Passwords do not match"}), 400

        # Check if Super Admin exists
        existing_sa = SuperAdmin.query.filter_by(email=email).first()
        if existing_sa:
            if existing_sa.is_verified:
                return jsonify({"message": "Super Admin already exists"}), 409
            else:
                # User exists but not verified (previous email failed) -> Resend OTP
                otp = existing_sa.generate_signup_otp()
                db.session.commit()
                if send_signup_otp(email, otp):
                    return jsonify({"message": "OTP resent to email"}), 200
                else:
                    return jsonify({"message": "Failed to resend OTP. Check server logs."}), 500

        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered in Users"}), 409

        hashed_password = generate_password_hash(data["password"])

        # 1. Create User Record (inactive until verified)
        new_user = User(
            email=email,
            password=hashed_password,
            role="SUPER_ADMIN",
            is_superadmin=True,
            is_active=False
        )
        db.session.add(new_user)
        db.session.flush() # Flush to generate new_user.id

        # 2. Create SuperAdmin Profile linked to User
        sa = SuperAdmin(
            user_id=new_user.id,
            email=email,
            password=hashed_password,
            first_name=data.get("first_name"),
            last_name=data.get("last_name")
        )

        otp = sa.generate_signup_otp()
        db.session.add(sa)
        db.session.commit()

        if send_signup_otp(email, otp):
            return jsonify({"message": "OTP sent to email"}), 201
        else:
            return jsonify({"message": "User created, but email failed. Check server logs."}), 201
    except Exception as e:
        import traceback
        current_app.logger.error(f"--- SIGNUP FAILED ---\n{traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"message": "An internal server error occurred during signup.", "error": str(e)}), 500

# -----------------------------
# 2️⃣ VERIFY SIGNUP OTP
# -----------------------------
@auth_bp.route("/verify-signup-otp", methods=["POST"])
def verify_signup_otp():
    data = request.get_json()

    email = data.get("email", "").lower().strip()
    otp = data.get("otp")

    sa = SuperAdmin.query.filter_by(email=email).first()
    if not sa or not sa.signup_otp:
        return jsonify({"message": "Invalid OTP"}), 400

    if sa.signup_otp != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    if sa.signup_otp_expiry < datetime.utcnow():
        return jsonify({"message": "OTP expired"}), 400

    sa.is_verified = True
    sa.signup_otp = None
    sa.signup_otp_expiry = None

    user = User.query.filter_by(email=sa.email).first()
    if user:
        user.is_active = True

    db.session.commit()

    return jsonify({"message": "Signup verified successfully"}), 200


# -----------------------------
# 3️⃣ LOGIN
# -----------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email", "").lower().strip()
    password = data.get("password")

    # 1. Check User table (Central Auth for ALL roles)
    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    # 2. Role-specific checks
    if user.role == "SUPER_ADMIN":
        sa = SuperAdmin.query.filter_by(email=email).first()
        if sa and not sa.is_verified:
            return jsonify({"message": "Please verify OTP first"}), 403
        
    if not user.is_active:
        return jsonify({"message": "Account is inactive"}), 403

    token = jwt.encode(
        {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "company_id": user.company_id
        },
        current_app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    # Frontend URL logic
    base_url = ""
    if user.role == "SUPER_ADMIN":
        base_url = f"http://localhost:5173/{user.email.split('@')[0]}"
    elif user.company:
        username = user.email.split("@")[0]
        company_code = user.company.company_code or ""
        subdomain = (user.company.subdomain or "").replace("http://", "").replace("https://", "").strip().strip("/")
        base_url = f"http://{username}{company_code}.{subdomain}"

    # Calculate login time in company timezone
    company_timezone = "UTC"
    if user.company and hasattr(user.company, 'timezone') and user.company.timezone:
        company_timezone = user.company.timezone

    try:
        tz = ZoneInfo(company_timezone)
    except Exception:
        tz = timezone.utc

    login_time_local = datetime.now(tz).strftime("%d %b %Y, %I:%M %p")

    # Send login notifications (Security Alert + Success Confirmation)
    send_security_alert_email(user.email, login_time_local)
    send_login_success_email(user.email, login_time_local)

    return jsonify({
        "message": "Login successful",
        "token": token,
        "role": user.role,
        "base_url": base_url,
        "login_time_local": login_time_local
    }), 200


# -----------------------------
# 4️⃣ FORGOT PASSWORD
# -----------------------------
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email", "").lower().strip()

    sa = SuperAdmin.query.filter_by(email=email).first()
    if not sa:
        return jsonify({"message": "User not found"}), 404

    otp = sa.generate_reset_otp()
    db.session.commit()

    if send_reset_otp(email, otp):
        return jsonify({"message": "Reset OTP sent to email"}), 200
    else:
        return jsonify({"message": "Error sending email"}), 500


# -----------------------------
# 5️⃣ VERIFY RESET OTP
# -----------------------------
@auth_bp.route("/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    data = request.get_json()
    email = data.get("email", "").lower().strip()
    otp = data.get("otp")

    sa = SuperAdmin.query.filter_by(email=email).first()
    if not sa or not sa.reset_otp:
        return jsonify({"message": "Invalid OTP request"}), 400

    if sa.reset_otp != otp:
        return jsonify({"message": "Invalid OTP"}), 400

    if sa.reset_otp_expiry < datetime.utcnow():
        return jsonify({"message": "OTP expired"}), 400

    session["reset_email"] = sa.email
    session["reset_verified_at"] = datetime.utcnow().isoformat()

    return jsonify({"message": "OTP verified successfully"}), 200


# -----------------------------
# 6️⃣ RESET PASSWORD
# -----------------------------
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    new_password = data.get("password")
    confirm_password = data.get("confirm_password")

    email = session.get("reset_email")
    if not email:
        return jsonify({"message": "Verify reset OTP first"}), 403

    if new_password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    sa = SuperAdmin.query.filter_by(email=email).first()
    if not sa:
        return jsonify({"message": "User not found"}), 404

    hashed = generate_password_hash(new_password)
    sa.password = hashed
    sa.reset_otp = None
    sa.reset_otp_expiry = None

    user = User.query.filter_by(email=email).first()
    if user:
        user.password = hashed

    db.session.commit()
    session.pop("reset_email", None)
    session.pop("reset_verified_at", None)

    return jsonify({"message": "Password reset successfully"}), 200


# -----------------------------
# 7️⃣ REGISTER COMPANY (New Client)
# -----------------------------
@auth_bp.route("/register-company", methods=["POST"])
def register_company():
    try:
        data = request.get_json()
        
        # Basic Validation
        required_fields = ["company_name", "subdomain", "email", "password", "first_name", "last_name"]
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing required fields"}), 400

        email = data["email"].lower().strip()
        subdomain = data["subdomain"].lower().strip()

        # Check Duplicates
        if Company.query.filter_by(subdomain=subdomain).first():
            return jsonify({"message": "Subdomain already taken"}), 409
        
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered"}), 409

        # 1. Create Company
        new_company = Company(
            company_name=data["company_name"],
            subdomain=subdomain,
            email=email,
            company_code=data.get("company_code")
        )
        db.session.add(new_company)
        db.session.flush()

        # 2. Create Admin User
        hashed_password = generate_password_hash(data["password"])
        new_user = User(
            email=email,
            password=hashed_password,
            role="ADMIN",
            company_id=new_company.id,
            is_active=True
        )
        db.session.add(new_user)
        db.session.flush()

        # 3. Create Employee Profile for Admin
        new_employee = Employee(
            user_id=new_user.id,
            company_id=new_company.id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            designation="Company Admin",
            department="Management",
            employee_id="ADMIN-01"
        )
        db.session.add(new_employee)
        db.session.commit()

        return jsonify({"message": "Company registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Registration failed", "error": str(e)}), 500
