from flask import Flask, request, jsonify
import logging
from datetime import timedelta
import re
from flask_cors import CORS
from models import db
from config import Config
from flask_migrate import Migrate

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.employee import employee_bp
from routes.attendance import attendance_bp
from routes.documents import documents_bp
from routes.payroll import payroll_bp
from routes.user import user_bp
from routes.policies import policies_bp
from leave import leave_bp
from routes.approvals import approvals_bp
from routes.company import company_bp # Corrected import
from routes.hr_documents import hr_docs_bp
from routes.profile_routes import profile_bp

# Ensure UserPermission model is imported so SQLAlchemy can resolve the relationship in User model.
from models.user_permission import UserPermission
# Ensure Department model is imported so SQLAlchemy can resolve the relationship in Company model.
from models.department import Department
# Ensure Designation model is imported so SQLAlchemy can resolve the relationship in Company/Employee model.
from models.designation import Designation
# Ensure BankDetails model is imported so SQLAlchemy can resolve the relationship in Employee model.
from models.bank_details import BankDetails
# Ensure Branch model is imported for Flask-Migrate
from models.branch import Branch

app = Flask(__name__)
app.config.from_object(Config)

# ✅ Enable Request Logging (To see if frontend is connecting)
logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    app.logger.info(f"📡 Incoming Request: {request.method} {request.url} | Origin: {request.headers.get('Origin')}")
    print(f"📡 HIT: {request.method} {request.url}")  # Force print to terminal

app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

CORS(
    app,
    resources={r"/api/*": {
        "origins": [
            "http://localhost:5173",      # Vite
            "http://localhost:5174",      # Vite (alternative port)
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://localhost:3000",      # For Create React App
            re.compile(r"^http://192\.168\..*:\d+$")  # Any local network IP on any port
        ]
    }},
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True
)
CORS(app, resources={r"/*": {"origins": "*"}})

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")

app.register_blueprint(hr_bp, url_prefix="/api/hr")
app.register_blueprint(employee_bp, url_prefix="/api")
app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
app.register_blueprint(documents_bp, url_prefix="/api/documents")
app.register_blueprint(payroll_bp, url_prefix="/api")
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(policies_bp, url_prefix="/api/policies")
app.register_blueprint(leave_bp)
app.register_blueprint(approvals_bp, url_prefix="/api/approvals")
app.register_blueprint(company_bp, url_prefix="/api/superadmin") # Corrected registration and prefix
app.register_blueprint(hr_docs_bp, url_prefix="/api/hr-docs")
app.register_blueprint(profile_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
