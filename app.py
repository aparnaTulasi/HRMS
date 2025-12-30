# c:\Users\DELL5410\Desktop\HRMS\app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from models.master import db, UserMaster

# Import Blueprints
from auth.routes import auth_bp
from superadmin.routes import superadmin_bp
from employee.routes import employee_bp
from admin.routes import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"], "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})
db.init_app(app)

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")
app.register_blueprint(employee_bp, url_prefix="/api/employee")
app.register_blueprint(admin_bp, url_prefix="/api/admin")

@app.route("/")
def home():
    return {
      "endpoints": {
        "admin": {
          "create_employee": "POST /api/admin/employee",
          "delete_employee": "DELETE /api/admin/employee/<id>",
          "get_employee": "GET /api/admin/employee/<id>",
          "get_employees": "GET /api/admin/employees",
          "update_employee": "PUT /api/admin/employee/<id>",
          "approve_user": "POST /api/admin/approve-user/<id>"
        },
        "auth": {
          "login": "POST /api/auth/login",
          "logout": "POST /api/auth/logout",
          "profile": "GET /api/auth/profile",
          "register": "POST /api/auth/register"
        },
        "superadmin": {
          "create_company": "POST /api/superadmin/create-company",
          "get_companies": "GET /api/superadmin/companies",
          "get_company": "GET /api/superadmin/company/<id>"
        },
        "employee": {
          "profile": "GET /api/employee/profile",
          "attendance": "POST /api/employee/attendance"
        }
      },
      "message": "HRMS Multi-Tenant API",
      "version": "1.0.0"
    }

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        # Check if database is seeded
        if not UserMaster.query.first():
            print("\n⚠️  WARNING: Database is empty.\n")
            
    app.run(debug=True, port=5000)
