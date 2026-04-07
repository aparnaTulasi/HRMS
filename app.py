import logging
import os
from datetime import timedelta
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db
from config import Config
from flask_migrate import Migrate

# ✅ Enable Logging at the very start
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[
        logging.FileHandler("backend_error.log"),
        logging.StreamHandler()
    ]
)

# Import Blueprints
# ... (rest of imports)
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.employee import employee_bp
from routes.attendance import attendance_bp
from routes.attendance_features import attendance_features_bp
from routes.documents import documents_bp
from routes.payroll import payroll_bp
from routes.announcement_routes import announcement_bp
from routes.exit_routes import exit_bp
from routes.manager import manager_bp
from routes.user import user_bp
from routes.policies import policies_bp
from leave import leave_bp
from routes.approvals import approvals_bp
from routes.company import company_bp
from routes.hr_documents import hr_docs_bp
from routes.profile_routes import profile_bp
from routes.profile_approval_routes import profile_approval_bp
from routes.audit_log import audit_bp
from routes.support import support_bp
from routes.calendar import calendar_bp
from routes.assets import assets_bp
from routes.id_card import id_card_bp
from routes.wfh import wfh_bp
from routes.feedback import feedback_bp
from routes.loan_routes import loan_bp
from routes.team_routes import team_bp
from routes.recruitment_routes import recruit_bp
from routes.onboarding import onboarding_bp
from routes.department_routes import dept_bp
from routes.access_control import access_control_bp
from routes.training_routes import training_bp
from routes.expense_routes import expense_bp
from routes.dashboard_routes import dashboard_bp
from routes.visitor_routes import visitor_bp
from routes.desk_routes import desk_bp
from routes.delegation_routes import delegation_bp
from routes.document_center_routes import doc_center_bp
from routes.main_routes import main_bp
from routes.desk_routes import desk_bp
from routes.document_center_routes import doc_center_bp

from models.permission import Permission, UserPermission
from models.department import Department
from models.designation import Designation
from models.bank_details import BankDetails
from models.branch import Branch
from models.employee_statutory import Form16, FullAndFinal
from models.squad import Squad
from models.squad_member import SquadMember
from models.job_posting import JobPosting
from models.job_applicant import JobApplicant
from models.profile_change_request import ProfileChangeRequest
from models.profile_change_request_item import ProfileChangeRequestItem
from models.notification import Notification
from models.visitor import VisitorRequest
from models.desk import Desk, DeskBooking

app = Flask(__name__)
app.config.from_object(Config)

@app.before_request
def log_request_info():
    app.logger.info(f"[API] Incoming Request: {request.method} {request.url} | Origin: {request.headers.get('Origin')}")
    print(f"[API] HIT: {request.method} {request.url}", flush=True)

app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

# ✅ Unified CORS Configuration
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization"]
)

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")

app.register_blueprint(hr_bp, url_prefix="/api/hr")
app.register_blueprint(employee_bp, url_prefix="/api")
app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
app.register_blueprint(attendance_features_bp) # url_prefix is defined in the blueprint
app.register_blueprint(documents_bp, url_prefix="/api/documents")
app.register_blueprint(payroll_bp, url_prefix="/api")
app.register_blueprint(announcement_bp, url_prefix='/api/announcements')
app.register_blueprint(exit_bp, url_prefix='/api/exit')
app.register_blueprint(manager_bp, url_prefix='/api/manager')
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(policies_bp, url_prefix="/api/policies")
app.register_blueprint(leave_bp)
app.register_blueprint(approvals_bp, url_prefix="/api/approvals")
app.register_blueprint(company_bp, url_prefix="/api/superadmin") # Corrected registration and prefix
app.register_blueprint(hr_docs_bp, url_prefix="/api/hr-docs")
app.register_blueprint(profile_bp)
app.register_blueprint(profile_approval_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(support_bp, url_prefix="/api/support")
app.register_blueprint(calendar_bp, url_prefix="/api/calendar")
app.register_blueprint(assets_bp, url_prefix="/api/assets")
app.register_blueprint(id_card_bp, url_prefix="/api/id-card")
app.register_blueprint(wfh_bp, url_prefix="/api/wfh")
app.register_blueprint(feedback_bp, url_prefix="/api")
app.register_blueprint(loan_bp, url_prefix="/api/loans")
app.register_blueprint(team_bp)
app.register_blueprint(recruit_bp)
app.register_blueprint(onboarding_bp, url_prefix="/api/hr/onboarding")
app.register_blueprint(dept_bp, url_prefix="/api")
app.register_blueprint(access_control_bp, url_prefix="/api/admin/access-control")
app.register_blueprint(training_bp, url_prefix="/api/hr/training")
app.register_blueprint(expense_bp, url_prefix="/api/expenses")
app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
app.register_blueprint(visitor_bp, url_prefix='/api/visitor')
app.register_blueprint(desk_bp, url_prefix='/api/desk')
app.register_blueprint(delegation_bp, url_prefix='/api/delegation')
app.register_blueprint(doc_center_bp, url_prefix='/api/document-center')
app.register_blueprint(main_bp)

@app.route('/')
def home():
    return jsonify({
        "message": "HRMS Backend is running",
        "status": "success",
        "endpoints": ["/api/auth", "/api/admin", "/api/employee", "/api/attendance"]
    }), 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

# Alias for misconfigured frontend hitting /login instead of /api/auth/login
@app.route('/login', methods=['POST'])
def root_login_alias():
    from routes.auth import login as auth_login
    return auth_login()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
