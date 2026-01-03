# c:\Users\DELL5410\Desktop\HRMS\app.py
import os

from flask import Flask
from flask_cors import CORS
from sqlalchemy import inspect

from config import Config
from models.master import db, UserMaster
from models.master_employee import Employee

# Blueprints
from auth.routes import auth_bp
from superadmin.routes import superadmin_bp
from employee.employee_routes import employee_bp
from admin.routes import admin_bp
from hr.routes import hr_bp
from employee.employee_documents import employee_documents_bp

app = Flask(__name__)
app.config.from_object(Config)

# Ensure absolute path for master.db to avoid duplicates
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'master.db')}"

# Debug: Print the actual database path on startup to verify location
print(f"\n✅ REAL DB PATH: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

# Enable CORS
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        }
    }
)

# Init DB
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")
app.register_blueprint(employee_bp, url_prefix="/api/employee")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(hr_bp, url_prefix="/api/hr")
app.register_blueprint(employee_documents_bp, url_prefix="/api/employee-documents")

# Home Route (ENDPOINTS LIST INCLUDED ✅)
@app.route("/")
def home():
    return {
        "message": "HRMS Multi-Tenant API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "logout": "POST /api/auth/logout",
                "profile": "GET /api/auth/profile",
                "get_master_employees": "GET /api/auth/master-employees",
                "sync_employees": "POST /api/auth/sync-employees"
            },
            "superadmin": {
                "create_company": "POST /api/superadmin/create-company",
                "get_companies": "GET /api/superadmin/companies",
                "get_company": "GET /api/superadmin/company/<id>"
            },
            "admin": {
                "create_employee": "POST /api/admin/employee",
                "update_employee": "PUT /api/admin/employee/<id>",
                "delete_employee": "DELETE /api/admin/employee/<id>",
                "get_employee": "GET /api/admin/employee/<id>",
                "get_employees": "GET /api/admin/employees",
                "approve_user": "POST /api/admin/approve-user/<id>",
                "dashboard_stats": "GET /api/admin/dashboard-stats",
                "verify_document": "PUT /api/admin/document/<id>/verify"
            },
            "hr": {
                "get_employees": "GET /api/hr/employees",
                "get_employee": "GET /api/hr/employee/<id>",
                "update_employee": "PUT /api/hr/employee/<id>",
                "delete_employee": "DELETE /api/hr/employee/<id>",
                "get_departments": "GET /api/hr/departments"
            },
            "employee": {
                "profile": "GET /api/employee/profile",
                "attendance": "POST /api/employee/attendance"
            },
            "employee_documents": {
                "upload": "POST /api/employee-documents/upload",
                "list": "GET /api/employee-documents/my-documents",
                "delete": "DELETE /api/employee-documents/<id>"
            }
        }
    }

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        inspector = inspect(db.engine)
        print("✅ Tables in DB:", inspector.get_table_names())

        if not UserMaster.query.first():
            print("\n⚠️ WARNING: Database is empty. Run 'python seed_hrms.py' to populate it.\n")

    app.run(debug=True, port=5000)
